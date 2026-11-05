# Diagram ERD bazy danych

Wygenerowany ze schematu aplikacji (`Base.metadata`). Stan: tydzień 2. Tabela `bank_profiles` dojdzie w etapie 4.

```mermaid
erDiagram
    users |o--o{ categories : "user_id"
    categories |o--o{ transactions : "category_id"
    import_batches |o--o{ transactions : "import_batch_id"
    users ||--o{ transactions : "user_id"
    users ||--o{ import_batches : "user_id"
    categories ||--o{ category_rules : "category_id"
    users |o--o{ category_rules : "user_id"
    users ||--o{ ai_advice : "user_id"

    users {
        int id PK
        varchar email UK
        varchar password_hash
        timestamptz created_at
    }
    categories {
        int id PK
        int user_id FK "NULL"
        varchar name
        varchar color "NULL"
        varchar icon "NULL"
        bool is_income
    }
    transactions {
        int id PK
        int user_id FK
        date date
        date booking_date "NULL"
        numeric amount
        varchar currency
        text description
        text description_normalized "NULL"
        varchar counterparty "NULL"
        int category_id FK "NULL"
        int import_batch_id FK "NULL"
        enum source
        enum kind
        varchar dedup_hash "NULL"
        timestamptz created_at
    }
    import_batches {
        int id PK
        int user_id FK
        varchar bank
        varchar filename
        int rows_total
        int rows_imported
        int rows_duplicated
        timestamptz created_at
    }
    category_rules {
        int id PK
        int user_id FK "NULL"
        varchar pattern
        enum match_type
        int category_id FK
        int priority
        enum source
        timestamptz created_at
    }
    ai_advice {
        int id PK
        int user_id FK
        date period_start
        date period_end
        varchar provider
        varchar model
        jsonb prompt_payload
        text response_text
        int tokens_in "NULL"
        int tokens_out "NULL"
        timestamptz created_at
    }
```

**Reguły usuwania:** usunięcie użytkownika kasuje wszystkie jego dane. Usunięcie kategorii lub importu zostawia
transakcje bez powiązania, a reguły znikają razem ze swoją kategorią.

**Unikalność złożona:** `categories (user_id, name)` i `transactions (user_id, dedup_hash)`.

**Wartość `NULL` właściciela** w `categories` i `category_rules` oznacza kategorię lub regułę systemową.
