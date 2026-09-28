# API-PIP

Учебный API-пайплайн: CSV с отзывами → Google Gemini LLM → структурированный
JSON.

Скрипт читает отзывы на русском языке, определяет тональность
(`positive`, `negative`, `neutral`), основную тему и уверенность модели. Ответ
LLM проверяется по строгой Pydantic-схеме и только после этого сохраняется в
JSON.

## Структура проекта

```text
API-PIP/
├── data/reviews.csv          # входные данные
├── results/                  # результат работы
├── tests/test_main.py        # тесты чтения и сохранения данных
├── main.py                   # основной скрипт
├── requirements.txt
└── .env.example
```

## Требования

- Python 3.10 или новее;
- бесплатный API-ключ Gemini из Google AI Studio.

## Установка и запуск

```bash
git clone <ССЫЛКА_НА_РЕПОЗИТОРИЙ>/API-PIP.git
cd API-PIP
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export GEMINI_API_KEY="ваш_ключ"
python main.py
```

По умолчанию используются файлы `data/reviews.csv` и
`results/reviews_analysis.json`. Параметры можно изменить:

```bash
python main.py \
  --input data/reviews.csv \
  --output results/reviews_analysis.json \
  --model gemini-3.1-flash-lite \
  --batch-size 10
```

Ключ хранится только в переменной окружения и не записывается в репозиторий.
Модель также можно переопределить переменной `GEMINI_MODEL`.

Ключ можно бесплатно создать на странице
[Google AI Studio API Keys](https://aistudio.google.com/app/apikey). Модель
`gemini-3.1-flash-lite` имеет бесплатный тариф с лимитами запросов; актуальные
условия указаны в [официальном прайсе Gemini API](https://ai.google.dev/gemini-api/docs/pricing).

## Формат входных данных

CSV в кодировке UTF-8 с обязательными столбцами `id` и `text`:

```csv
id,text
1,"Наушники звучат отлично, басы глубокие, покупкой очень доволен."
2,"Заказ задержали на неделю, коробка пришла помятая."
```

Идентификаторы должны быть уникальными, значения `id` и `text` — непустыми.

## Формат результата

После реального вызова API создаётся JSON следующей структуры (значения ниже
показаны только как иллюстрация формата):

```json
{
  "metadata": {
    "source_file": "reviews.csv",
    "model": "gemini-3.1-flash-lite",
    "generated_at": "<UTC timestamp>",
    "items_count": 2
  },
  "results": [
    {
      "id": "1",
      "sentiment": "positive",
      "topic": "product_quality",
      "confidence": 0.98
    }
  ]
}
```

Допустимые темы: `product_quality`, `delivery`, `customer_service`, `price`,
`usability`, `other`.

## Проверка

Юнит-тесты не обращаются к API и не расходуют средства:

```bash
python -m unittest discover -s tests -v
```

Перед сдачей убедитесь, что файл `results/reviews_analysis.json` создан именно
реальным запуском скрипта и добавлен в Git.

## Как работает пайплайн

1. `load_reviews` читает CSV и проверяет обязательные поля и уникальность ID.
2. `analyze_reviews` отправляет отзывы пакетами через Gemini Interactions API.
3. Gemini Structured Outputs требует JSON по схеме `ReviewAnalysisBatch`.
4. Скрипт дополнительно сверяет набор ID с входными данными.
5. `save_result` записывает метаданные и результаты в UTF-8 JSON.

Документация Gemini: [быстрый старт](https://ai.google.dev/gemini-api/docs/get-started)
и [Structured Outputs](https://ai.google.dev/gemini-api/docs/structured-output).
