-- Step 1: Create illegal_trade_products table
CREATE TABLE illegal_trade_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_code VARCHAR(20) UNIQUE NOT NULL,
    product_name VARCHAR(100) NOT NULL,
    product_category VARCHAR(50),
    main_category VARCHAR(50),
    is_high_value BOOLEAN DEFAULT FALSE,
    search_terms TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);