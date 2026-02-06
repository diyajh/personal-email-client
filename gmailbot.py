import os
import re
import base64
from email.mime.text import MIMEText
from docx import Document

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]

# ---------- WORD FILE (BRAIN) ----------

from rank_bm25 import BM25Okapi
# simple tokenizer: lowercase words only
def tokenize(text: str):
    return re.findall(r"[a-z0-9]+", text.lower())

def load_rulebook(path="bot_test.docx"):
    doc = Document(path)
    rules = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return rules

def pick_best_rule(email_text: str, rules: list[str], top_k: int = 5):
    tokenized_rules = [tokenize(r) for r in rules]
    bm25 = BM25Okapi(tokenized_rules)

    query = tokenize(email_text)
    scores = bm25.get_scores(query)

    # sort best-first
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

    # DEBUG: show top matches
    print("\nTOP MATCHES (score | rule preview):")
    for idx, score in ranked[:top_k]:
        preview = rules[idx][:120].replace("\n", " ")
        print(f"{score:.2f} | {preview}")

    best_idx, best_score = ranked[0]
    print("BEST SCORE:", best_score)

    # If best score is too low, treat as "no match"
    

    if best_score < 0.2:
   # you can adjust this threshold later
        return None

    return rules[best_idx]


# ---------- EMAIL HELPERS ----------

def decode_part_data(data: str) -> str:
    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

def strip_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", html)
    text = re.sub(r"(?s)<.*?>", "", html)
    return re.sub(r"\n{3,}", "\n\n", text).strip()

def find_best_body(payload) -> str:
    plain = None
    html = None

    stack = [payload]
    while stack:
        p = stack.pop()
        mime = p.get("mimeType", "")
        data = (p.get("body") or {}).get("data")

        if data:
            if mime == "text/plain" and plain is None:
                plain = decode_part_data(data)
            elif mime == "text/html" and html is None:
                html = decode_part_data(data)

        for child in p.get("parts", []) or []:
            stack.append(child)

    if plain:
        return plain
    if html:
        return strip_html(html)

    return ""

def get_headers(msg) -> dict:
    return {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}

def create_reply_draft(service, thread_id, to_email, subject, body):
    if not subject.lower().startswith("re:"):
        subject = "Re: " + subject

    mime = MIMEText(body, "plain", "utf-8")
    mime["to"] = to_email
    mime["subject"] = subject

    raw = base64.urlsafe_b64encode(mime.as_bytes()).decode("utf-8")

    return service.users().drafts().create(
        userId="me",
        body={"message": {"raw": raw, "threadId": thread_id}}
    ).execute()

# ---------- MAIN ----------

def main():
    # Auth
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as f:
            f.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)

    # Load rulebook
    rules = load_rulebook()
    print(f"Loaded {len(rules)} rules from Word file")

    # Get 1 unread email
    res = service.users().messages().list(
        userId="me",
        q="is:unread in:inbox",
        maxResults=1
    ).execute()

    msgs = res.get("messages", [])
    if not msgs:
        print("No unread emails.")
        return

    msg = service.users().messages().get(
        userId="me",
        id=msgs[0]["id"],
        format="full"
    ).execute()

    headers = get_headers(msg)
    sender = headers.get("From", "")
    subject = headers.get("Subject", "")
    thread_id = msg["threadId"]

    m = re.search(r"<([^>]+)>", sender)
    to_email = m.group(1) if m else sender

    body = find_best_body(msg["payload"])

    print("\nEMAIL BODY PREVIEW:\n", body[:300])

    # Use Word brain
    rule = pick_best_rule(body, rules)


    if rule:
        reply = f"Hi,\n\n{rule}\n\nBest,\nDiya"
    else:
        reply = (
            "Hi,\n\n"
            "Thanks for your email. I’ve received it and will get back to you shortly.\n\n"
            "Best,\n"
            "Diya"
        )

    create_reply_draft(service, thread_id, to_email, subject, reply)
    print("✅ Draft created using Word file")

if __name__ == "__main__":
    main()



