# Assist: Email Reply Assistant

A Python tool that drafts replies to incoming Gmail messages from an organization's own FAQ document. It reads an unread email, finds the most relevant answer in a Word file of approved responses, and saves a reply draft in Gmail for a person to review before sending.

## How It Works

1. **Load the knowledge base.** Each paragraph of `bot_test.docx` becomes one answer.
2. **Fetch an unread email** from the inbox using the Gmail API.
3. **Retrieve the best answer.** BM25 ranks every answer against the email body and picks the top match.
4. **Fall back safely.** If no answer scores above the threshold, the tool writes a short acknowledgment instead of guessing.
5. **Save a draft, never send.** The reply is saved as a draft in the original thread.

## Safety by Design

- Requests only two Gmail permissions: read (`gmail.readonly`) and create drafts (`gmail.compose`). It cannot send email.
- Every reply waits in Drafts for human review.
- Answers come only from the organization's own document, so replies stay grounded in approved information.

## Tech Stack

| Area | Tools |
|---|---|
| Language | Python |
| Retrieval | rank-bm25 |
| Email | Gmail API (google-api-python-client, google-auth-oauthlib) |
| Knowledge base | Word document (python-docx) |

## Getting Started

1. Install dependencies:

   ```bash
   pip install google-api-python-client google-auth-oauthlib python-docx rank-bm25
   ```

2. Create an OAuth client in Google Cloud Console with the Gmail API enabled, then save the file as `credentials.json` in the project folder.

3. Put your FAQ answers in `bot_test.docx`, one answer per paragraph.

4. Run the script:

   ```bash
   python gmailbot.py
   ```

   On the first run, a browser window opens so you can sign in to Google. Your sign-in token is saved to `token.json`.

`credentials.json` and `token.json` are listed in `.gitignore` and should never be committed.
