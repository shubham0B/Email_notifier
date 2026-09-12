import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Establishes connection to personal_whatsapp_db."""
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_USER", "root")
    password = os.getenv("MYSQL_PASSWORD", "")
    database = os.getenv("MYSQL_DATABASE", "personal_whatsapp_db")

    if not password:
        return None

    try:
        import pymysql
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset="utf8mb4",
            autocommit=True
        )
        return conn
    except Exception as e:
        # Fallback to mysql.connector if installed
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database
            )
            return conn
        except Exception:
            return None

def save_digest_run(
    target_date: str,
    mode: str,
    processed_emails: List[Dict[str, Any]],
    news_data: Dict[str, Any],
    pdf_path: Optional[str] = None
) -> Optional[str]:
    """Saves digest run, emails, and news items to personal_whatsapp_db."""
    conn = get_db_connection()
    if not conn:
        return None

    digest_id = str(uuid.uuid4())
    urgent_count = sum(1 for e in processed_emails if "urgent" in str(e.get("category", "")).lower())
    pdf_filename = os.path.basename(pdf_path) if pdf_path else None

    try:
        with conn.cursor() as cursor:
            # 1. Insert master digest record
            sql_digest = """
            INSERT INTO digests (id, target_date, mode, total_emails, urgent_count, pdf_filename, pdf_path, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql_digest, (
                digest_id,
                target_date or datetime.now().strftime("%Y-%m-%d"),
                mode.upper() if mode else "TODAY",
                len(processed_emails),
                urgent_count,
                pdf_filename,
                pdf_path,
                "GENERATED"
            ))

            # 2. Insert individual emails
            sql_email = """
            INSERT INTO digest_emails (digest_id, sender_name, sender_email, subject, category, urgency_level, summary, arrival_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            for em in processed_emails:
                cursor.execute(sql_email, (
                    digest_id,
                    em.get("sender_name", "")[:255],
                    em.get("sender", "")[:255],
                    em.get("subject", "")[:500],
                    em.get("category", "")[:100],
                    em.get("urgency_level", "NORMAL")[:50],
                    em.get("summary", ""),
                    em.get("time_str", "")[:50]
                ))

            # 3. Insert news items if present
            if news_data:
                sql_news = """
                INSERT INTO digest_news (digest_id, category, headline, source, url)
                VALUES (%s, %s, %s, %s, %s)
                """
                for cat_name, articles in news_data.items():
                    if isinstance(articles, list):
                        for art in articles:
                            cursor.execute(sql_news, (
                                digest_id,
                                cat_name[:100],
                                str(art.get("title", ""))[:500],
                                str(art.get("source", ""))[:255],
                                str(art.get("url", ""))[:500]
                            ))

        conn.commit()
        print(f"💾 [MySQL] Digest successfully recorded into personal_whatsapp_db (ID: {digest_id})")
        return digest_id
    except Exception as e:
        print(f"⚠️ [MySQL] Could not save digest to database: {e}")
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass

def log_whatsapp_dispatch(
    digest_id: Optional[str],
    recipient: str,
    message_type: str,
    status: str,
    message_id: Optional[str] = None,
    error_message: Optional[str] = None
):
    """Logs WhatsApp message dispatch event."""
    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            sql = """
            INSERT INTO whatsapp_dispatches (digest_id, recipient, message_type, status, message_id, error_message)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                digest_id,
                recipient[:50],
                message_type.upper(),
                status.upper(),
                (message_id or "")[:100],
                error_message
            ))
        conn.commit()
    except Exception as e:
        print(f"⚠️ [MySQL] Could not log WhatsApp dispatch: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass
