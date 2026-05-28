# LexAI Competition Pack V2 + V3

Folder nay la ban hop nhat de dung cho NotebookLM tao slide va video.

## File moi nhat (V3 — chi tiet nhat)

**`VIDEO_DEMO_PLAN_V3.md`** — Ke hoach video demo V3, chi tiet nhat:
- Persona driven: Chi Mai, cong nhan may bi sa thai (lao_dong domain)
- Script loi thoai chinh xac theo tung giay (0:00-10:00)
- Click sequence: Analyze → NBA chip → SimilarCases (auto-run) → Community Cases → Dashboard → MongoDB Atlas
- Pre-recording setup: exact commands, MongoDB Atlas tab setup, data seeding
- Fallback plan cho 4 loai su co pho bien
- Phase 23 Community Intelligence highlight
- Phase 24 Document Enrichment mention
- Judge rubric alignment (MongoDB competition criteria)
- Final checklist 10 diem truoc khi nop

**`scripts/seed_video_demo.py`** — Script seed du lieu demo:
```powershell
python scripts/seed_video_demo.py          # seed lao_dong interactions cho demo_user_001
python scripts/seed_video_demo.py --dry-run  # kiem tra truoc khi chay that
```

## Ket luan so sanh nhanh

Nen dung `competition/` lam base chinh, vi bo nay bam dung goc nhin cuoc thi: MongoDB Recommendation Engine, Vector Search, Aggregation Pipeline, collaborative filtering, personalization va technical docs.

Nen lay `video/` lam chat lieu loi thoai va storyboard, vi bo nay co giong ke chuyen tot hon, canh demo cu the hon va nhan manh UX san pham ro hon.

Ban V2 trong folder nay hop nhat ca hai:

- Giu goc nhin MongoDB-first cua `competition/`.
- Lay do “thuc te san pham” cua `video/`.
- Cat bot cac khang dinh qua da nhu “chinh xac tuyet doi”, “top 1 chac chan”, “cao cap” lap lai.
- Tap trung vao luong demo co gia tri nhat: phan tich phap ly -> recommendation -> can cu -> hanh dong tiep theo -> hanh vi nguoi dung -> MongoDB deep dive.

## File nen paste vao NotebookLM

Paste file nay truoc:

1. `NOTEBOOKLM_MASTER_PLAN.md`

Sau do co the paste them file nay neu muon NotebookLM tao loi thoai video chi tiet hon:

2. `VIDEO_SCRIPT_10_MIN.md`

Neu muon giong video giong dang pitch san pham cho ban giam khao hon, paste file nay:

3. `AI_HOST_VIDEO_PLAN_FOR_JUDGES.md`

## File nen nop / dung de tao slide

- Slide deck: tao tu `NOTEBOOKLM_MASTER_PLAN.md`, muc "Slide Deck".
- Video: tao tu `VIDEO_SCRIPT_10_MIN.md`.
- Video giong product pitch cho judges: tao tu `AI_HOST_VIDEO_PLAN_FOR_JUDGES.md`.
- Technical summary: lay muc "Technical Proof Points" trong `NOTEBOOKLM_MASTER_PLAN.md`.

## Chien luoc nho khi quay

Dung mot demo flow duy nhat, dung nhay qua qua nhieu module. Ban giam khao can thay 3 dieu:

1. San pham giai quyet van de that.
2. Recommendation engine la that, co ranking, co behavior signal, co feedback loop.
3. MongoDB khong chi la noi luu data, ma la core retrieval + analytics + personalization engine.
