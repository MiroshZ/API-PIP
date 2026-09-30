# API-PIP

Учебный API-пайплайн: CSV с отзывами → LLM через GroqCloud → структурированный
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
- бесплатный API-ключ из GroqCloud.

## Установка и запуск

```bash
git clone https://github.com/MiroshZ/API-PIP.git
cd API-PIP
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export GROQ_API_KEY="ваш_ключ"
python main.py
```

По умолчанию используются файлы `data/reviews.csv` и
`results/reviews_analysis.json`. Параметры можно изменить:

```bash
python main.py \
  --input data/reviews.csv \
  --output results/reviews_analysis.json \
  --model openai/gpt-oss-20b \
  --batch-size 10
```

Ключ хранится только в переменной окружения и не записывается в репозиторий.
Модель также можно переопределить переменной `GROQ_MODEL`.

Ключ можно бесплатно создать на странице
[GroqCloud API Keys](https://console.groq.com/keys). Для модели
`openai/gpt-oss-20b` действует бесплатный тариф с лимитами запросов; актуальные
значения указаны в [официальной таблице лимитов](https://console.groq.com/docs/rate-limits).

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
    "model": "openai/gpt-oss-20b",
    "generated_at": "<UTC timestamp>",
    "items_count": 1
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

В папке `results` уже есть JSON с результатами для девяти отзывов из
`data/reviews.csv`. После изменения входного файла запустите скрипт повторно
и добавьте обновлённые CSV и JSON в Git перед сдачей.

## Как работает пайплайн

1. `load_reviews` читает CSV и проверяет обязательные поля и уникальность ID.
2. `analyze_reviews` отправляет отзывы пакетами через Groq Chat Completions API.
3. Groq Structured Outputs в строгом режиме требует JSON по схеме
   `ReviewAnalysisBatch`.
4. Скрипт дополнительно сверяет набор ID с входными данными.
5. `save_result` записывает метаданные и результаты в UTF-8 JSON.

Документация Groq: [быстрый старт](https://console.groq.com/docs/quickstart) и
[Structured Outputs](https://console.groq.com/docs/structured-outputs).
