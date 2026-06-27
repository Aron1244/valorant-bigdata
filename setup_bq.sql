-- ============================================
-- Setup BigQuery: tablas para votación streaming + batch
-- Ubicación del dataset: US-EAST4 (verificar con gcloud)
-- ============================================

-- Beneficencias
CREATE OR REPLACE TABLE valorant_dw.charities (
    charity_id INT64,
    charity_name STRING,
    description STRING
);

INSERT INTO valorant_dw.charities VALUES
(1, 'UNICEF', 'Ayuda humanitaria para la infancia a nivel global'),
(2, 'WWF', 'Conservación de la vida silvestre y la naturaleza'),
(3, 'Save the Children', 'Derechos y protección de la infancia'),
(4, 'Médicos Sin Fronteras', 'Asistencia médica en zonas de crisis'),
(5, 'Cruz Roja', 'Ayuda humanitaria en emergencias y desastres');

-- Skins en votación
CREATE OR REPLACE TABLE valorant_dw.voting_skins (
    skin_id INT64,
    skin_name STRING,
    weapon STRING,
    rarity STRING,
    base_price_vp INT64,
    description STRING
);

INSERT INTO valorant_dw.voting_skins VALUES
(1, 'Reaver Vandal', 'Vandal', 'Premium', 1775, 'Letal Vandal colección Reaver. Estética sombría con llamas violetas.'),
(2, 'Prime Phantom', 'Phantom', 'Premium', 1775, 'Futurista Phantom colección Prime. Diseño elegante con patrones dorados.');

-- ============================================
-- Votos (streaming) con campos enriquecidos
-- ============================================
CREATE OR REPLACE TABLE valorant_dw.votes (
    vote_id STRING,
    player_id STRING,
    skin_id INT64,
    charity_id INT64,
    voted_at TIMESTAMP,
    device_type STRING,
    session_minutes INT64,
    is_premium_player BOOL,
    vote_hour INT64,
    vote_day_of_week INT64
);

-- ============================================
-- Compras (streaming) con campos enriquecidos
-- ============================================
CREATE OR REPLACE TABLE valorant_dw.purchases (
    purchase_id STRING,
    player_id STRING,
    skin_id INT64,
    charity_id INT64,
    amount_vp INT64,
    purchased_at TIMESTAMP,
    donation_percent FLOAT64,
    payment_method STRING,
    is_discounted BOOL,
    purchase_hour INT64
);

-- ============================================
-- Log de actividad (API streaming)
-- ============================================
CREATE OR REPLACE TABLE valorant_dw.api_log (
    log_id STRING,
    event_type STRING,
    description STRING,
    created_at TIMESTAMP
);

-- ============================================
-- Log de actividad ETL (batch)
-- ============================================
CREATE OR REPLACE TABLE valorant_dw.etl_log (
    run_id STRING,
    table_name STRING,
    check_type STRING,
    description STRING,
    error_count INT64,
    run_time TIMESTAMP
);

-- ============================================
-- Vistas para Looker Studio
-- ============================================

CREATE OR REPLACE VIEW valorant_dw.analytics_voting AS
SELECT
    v.vote_id,
    v.player_id,
    vs.skin_name,
    vs.weapon,
    vs.rarity,
    c.charity_name AS charity_voted,
    v.voted_at,
    v.device_type,
    v.session_minutes,
    v.is_premium_player,
    v.vote_hour,
    v.vote_day_of_week
FROM valorant_dw.votes v
JOIN valorant_dw.voting_skins vs ON v.skin_id = vs.skin_id
JOIN valorant_dw.charities c ON v.charity_id = c.charity_id;

CREATE OR REPLACE VIEW valorant_dw.analytics_donations AS
SELECT
    p.purchase_id,
    p.player_id AS buyer_id,
    vs.skin_name,
    vs.weapon,
    vs.rarity,
    c.charity_name AS beneficiary,
    p.amount_vp,
    p.purchased_at,
    p.donation_percent,
    p.payment_method,
    p.is_discounted,
    p.purchase_hour
FROM valorant_dw.purchases p
JOIN valorant_dw.voting_skins vs ON p.skin_id = vs.skin_id
JOIN valorant_dw.charities c ON p.charity_id = c.charity_id;

-- ============================================
-- Vistas de calidad de datos
-- ============================================

-- Vista de control: votos duplicados (prevención)
CREATE OR REPLACE VIEW valorant_dw.v_dq_duplicate_votes AS
SELECT player_id, COUNT(*) AS vote_count, MIN(voted_at) AS first_vote, MAX(voted_at) AS last_vote
FROM valorant_dw.votes
GROUP BY player_id
HAVING COUNT(*) > 1;

-- Vista de control: anomalías en montos de compra
CREATE OR REPLACE VIEW valorant_dw.v_dq_anomalous_purchases AS
SELECT *, 'amount_vp fuera de rango normal' AS dq_issue
FROM valorant_dw.purchases
WHERE amount_vp <= 0 OR amount_vp > 10000;

-- Vista de control: registros huérfanos
CREATE OR REPLACE VIEW valorant_dw.v_dq_orphan_votes AS
SELECT v.*
FROM valorant_dw.votes v
LEFT JOIN valorant_dw.voting_skins vs ON v.skin_id = vs.skin_id
WHERE vs.skin_id IS NULL;
