import re, json, hashlib
import pdfplumber
import pandas as pd

def clean_text(t: str) -> str:
    t = t or ""
    t = re.sub(r"(\w)-\n(\w)", r"\1\2", t)
    t = t.replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

def extract_pages(pdf_path: str):
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, p in enumerate(pdf.pages):
            txt = clean_text(p.extract_text() or "")
            pages.append({"page": i + 1, "text": txt})
    return pages

def split_into_chunks(pages, chunk_chars=1800, overlap_chars=250):
    chunks = []
    for pg in pages:
        page_num = pg["page"]
        text = pg["text"]
        if not text:
            continue
        paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        buff = ""
        for para in paras:
            if len(buff) + len(para) + 2 <= chunk_chars:
                buff = buff + ("\n\n" if buff else "") + para
            else:
                if buff:
                    chunks.append({"page": page_num, "text": buff})
                tail = buff[-overlap_chars:] if overlap_chars and buff else ""
                buff = (tail + "\n\n" + para).strip()
        if buff:
            chunks.append({"page": page_num, "text": buff})

    for idx, c in enumerate(chunks):
        h = hashlib.md5((str(c["page"]) + "|" + c["text"][:200]).encode()).hexdigest()[:10]
        c["chunk_id"] = f"p{c['page']}_c{idx}_{h}"
    return chunks

def save_chunks(chunks, out_json_path: str):
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)




def extract_excel(path: str):
    df = pd.read_excel(path)
    text = "\n".join(
        df.astype(str)
          .fillna("")
          .values
          .flatten()
    )
    return [{"page": 1, "text": clean_text(text)}]

