# Market Intelligence MVP — Multi-Agent System

نظام ذكاء سوق MVP يعتمد على بنية Multi-Agent للتحليل والتجميع والإبلاغ.

## الهيكل (Project Structure)

```
market-intel-project/
├── .gitignore
├── README.md
├── main.py                 # المركز الرئيسي (Orchestrator)
├── brain/
│   └── logger_setup.py     # نظام السجلات
└── agents/
    ├── baseagent.py        # القالب الأساسي (Core Class)
    ├── filter_agent.py
    ├── hunter_agent.py
    └── sentiment_agent.py
```

## متطلبات التشغيل (Requirements)

- Python 3.8+
- المكتبات القياسية فقط (no external dependencies للنسخة الأساسية)

## التشغيل (Run)

```bash
git clone <repository-url>
cd market-intel-project
python main.py
```

## المعايير (Standards)

- **sys.path**: يُضبط في `main.py` لضمان عمل الاستيراد (imports) مباشرة بعد `git clone`.
- **المخرجات**: موحدة بصيغة `JSON Dictionary` لتسهيل الربط مع APIs لاحقاً.

## الوكلاء (Agents)

| Agent | الدور |
|-------|-------|
| Hunter | جمع البيانات والمصادر |
| Filter | تصفية وتنقية المدخلات |
| Sentiment | تحليل المشاعر والتوجه |

## الترخيص (License)

MIT
