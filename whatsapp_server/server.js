import fs from 'fs';
import path from 'path';
import express from 'express';
import makeWASocket, { 
    DisconnectReason, 
    useMultiFileAuthState,
    fetchLatestBaileysVersion
} from '@whiskeysockets/baileys';
import qrcode from 'qrcode-terminal';
import pino from 'pino';

const app = express();
app.use(express.json({ limit: '10mb' }));

const PORT = process.env.PORT || 3000;
let sock = null;
let isConnected = false;
let latestQrCode = null;
const messageStore = new Map();

async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState('./auth_info_baileys');
    const { version } = await fetchLatestBaileysVersion();

    sock = makeWASocket({
        version,
        logger: pino({ level: 'silent' }),
        printQRInTerminal: false,
        auth: state,
        getMessage: async (key) => {
            if (key?.id && messageStore.has(key.id)) {
                return messageStore.get(key.id);
            }
            return undefined;
        }
    });

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            console.log('\n=============================================================');
            console.log('📱 SCAN THIS QR CODE WITH YOUR WHATSAPP (Settings > Linked Devices):');
            console.log('=============================================================\n');
            qrcode.generate(qr, { small: true });
            console.log('\nWaiting for scan...');
        }

        if (connection === 'close') {
            const shouldReconnect = (lastDisconnect?.error)?.output?.statusCode !== DisconnectReason.loggedOut;
            console.log('⚠️ WhatsApp connection closed. Reconnecting:', shouldReconnect);
            isConnected = false;
            if (shouldReconnect) {
                setTimeout(connectToWhatsApp, 3000);
            }
        } else if (connection === 'open') {
            console.log('\n✅ WhatsApp Gateway Connected & Ready!');
            console.log(`🚀 REST API listening at: http://localhost:${PORT}`);
            isConnected = true;
        }
    });

    sock.ev.on('creds.update', saveCreds);
}

// Health check & status endpoints
app.get(['/', '/personal'], (req, res) => {
    if (req.headers.accept && req.headers.accept.includes('text/html')) {
        return res.sendFile(path.join(path.resolve(), 'public', 'pa_portal.html'));
    }
    res.json({ 
        service: "JECRC Personal WhatsApp Gateway",
        online: true,
        whatsapp_connected: isConnected,
        status: isConnected ? "CONNECTED" : "WAITING_FOR_QR_SCAN",
        port: PORT
    });
});

app.get(['/status', '/personal/status'], (req, res) => {
    res.json({ 
        online: true, 
        whatsapp_connected: isConnected,
        status: isConnected ? "CONNECTED" : "WAITING_FOR_QR_SCAN",
        port: PORT
    });
});

// Send text message endpoint
app.post('/send', async (req, res) => {
    try {
        const { number, message } = req.body;

        if (!number || !message) {
            return res.status(400).json({ error: 'Both "number" and "message" are required.' });
        }

        if (!isConnected || !sock) {
            return res.status(503).json({ error: 'WhatsApp gateway is not connected yet. Please scan QR code.' });
        }

        // Clean phone number format
        let cleanNumber = number.replace(/\D/g, '');
        if (!cleanNumber.endsWith('@s.whatsapp.net')) {
            cleanNumber = `${cleanNumber}@s.whatsapp.net`;
        }

        console.log(`📨 Sending message to ${cleanNumber}...`);
        const sent = await sock.sendMessage(cleanNumber, { text: message });
        if (sent?.key?.id && sent?.message) {
            messageStore.set(sent.key.id, sent.message);
        }

        res.json({ 
            success: true, 
            messageId: sent.key.id,
            to: cleanNumber 
        });
    } catch (error) {
        console.error('❌ Failed to send WhatsApp message:', error);
        res.status(500).json({ error: error.message });
    }
});

// Send document / PDF file endpoint
app.post('/send-document', async (req, res) => {
    try {
        const { number, filePath, fileName, caption, mimetype } = req.body;

        if (!number || !filePath) {
            return res.status(400).json({ error: 'Both "number" and "filePath" are required.' });
        }

        if (!isConnected || !sock) {
            return res.status(503).json({ error: 'WhatsApp gateway is not connected yet.' });
        }

        if (!fs.existsSync(filePath)) {
            return res.status(404).json({ error: `File not found on disk: ${filePath}` });
        }

        // Clean phone number format
        let cleanNumber = number.replace(/\D/g, '');
        if (!cleanNumber.endsWith('@s.whatsapp.net')) {
            cleanNumber = `${cleanNumber}@s.whatsapp.net`;
        }

        const fileBuffer = fs.readFileSync(filePath);
        const resolvedName = fileName || path.basename(filePath) || 'Daily_Executive_Digest.pdf';
        const resolvedMime = mimetype || 'application/pdf';

        console.log(`📎 Sending document "${resolvedName}" (${fileBuffer.length} bytes) to ${cleanNumber}...`);
        const sent = await sock.sendMessage(cleanNumber, {
            document: fileBuffer,
            mimetype: resolvedMime,
            fileName: resolvedName,
            caption: caption || ''
        });
        if (sent?.key?.id && sent?.message) {
            messageStore.set(sent.key.id, sent.message);
        }

        res.json({ 
            success: true, 
            messageId: sent.key.id,
            to: cleanNumber,
            fileName: resolvedName
        });
    } catch (error) {
        console.error('❌ Failed to send WhatsApp document:', error);
        res.status(500).json({ error: error.message });
    }
});

// ==========================================
// PA PORTAL & AGENDA MANAGEMENT API
// ==========================================
const SCHEDULE_FILE = path.join(path.resolve(), '..', 'data', 'pa_schedule.json');

// Serve static assets from public/
app.use(express.static(path.join(path.resolve(), 'public')));

app.get(['/pa', '/personal/pa'], (req, res) => {
    res.sendFile(path.join(path.resolve(), 'public', 'pa_portal.html'));
});

// GET PA schedule for target date
app.get(['/api/pa/schedule', '/pa/schedule'], (req, res) => {
    const targetDate = req.query.date || new Date().toISOString().split('T')[0];
    try {
        if (fs.existsSync(SCHEDULE_FILE)) {
            const data = JSON.parse(fs.readFileSync(SCHEDULE_FILE, 'utf-8'));
            return res.json(data[targetDate] || { meetings: [], reminders: [] });
        }
        return res.json({ meetings: [], reminders: [] });
    } catch (e) {
        return res.status(500).json({ error: e.message });
    }
});

// POST update PA schedule
app.post(['/api/pa/schedule', '/pa/schedule'], (req, res) => {
    const { date, meetings, reminders } = req.body;
    if (!date) {
        return res.status(400).json({ error: 'Date is required.' });
    }
    try {
        let store = {};
        if (fs.existsSync(SCHEDULE_FILE)) {
            try {
                store = JSON.parse(fs.readFileSync(SCHEDULE_FILE, 'utf-8'));
            } catch (err) {
                store = {};
            }
        }
        store[date] = {
            meetings: meetings || [],
            reminders: reminders || []
        };
        const dataDir = path.dirname(SCHEDULE_FILE);
        if (!fs.existsSync(dataDir)) {
            fs.mkdirSync(dataDir, { recursive: true });
        }
        fs.writeFileSync(SCHEDULE_FILE, JSON.stringify(store, null, 2), 'utf-8');
        return res.json({ success: true, date });
    } catch (e) {
        return res.status(500).json({ error: e.message });
    }
});

// Trigger daily briefing on-demand from PA portal
app.post(['/api/pa/trigger-briefing', '/pa/trigger-briefing'], (req, res) => {
    const targetDate = req.body.date || new Date().toISOString().split('T')[0];
    const projectRoot = path.resolve('..');

    console.log(`🚀 PA triggered briefing dispatch for date: ${targetDate}`);
    try {
        import('child_process').then(({ spawn }) => {
            const pyProcess = spawn('python', ['-X', 'utf8', 'main.py', '--live', '--gateway', '--date', targetDate], {
                cwd: projectRoot,
                detached: true,
                stdio: 'ignore'
            });
            pyProcess.unref();
        });
        return res.json({ success: true, message: `Briefing generation triggered for ${targetDate}` });
    } catch (e) {
        return res.status(500).json({ error: e.message });
    }
});

// Start server and connection
app.listen(PORT, () => {
    console.log(`📡 WhatsApp Gateway API Server running on port ${PORT}...`);
    console.log(`🏛️ PA Executive Portal active at: http://localhost:${PORT}/pa`);
    connectToWhatsApp();
});
