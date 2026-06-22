-- ============================================
-- Setup BigQuery: tablas para votación streaming
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

-- Votos (streaming)
CREATE OR REPLACE TABLE valorant_dw.votes (
    vote_id STRING,
    player_id STRING,
    skin_id INT64,
    charity_id INT64,
    voted_at TIMESTAMP
);

-- Compras (streaming)
CREATE OR REPLACE TABLE valorant_dw.purchases (
    purchase_id STRING,
    player_id STRING,
    skin_id INT64,
    charity_id INT64,
    amount_vp INT64,
    purchased_at TIMESTAMP
);

-- Log de actividad
CREATE OR REPLACE TABLE valorant_dw.api_log (
    log_id STRING,
    event_type STRING,
    description STRING,
    created_at TIMESTAMP
);

-- ============================================
-- Vistas para Looker Studio
-- ============================================

CREATE OR REPLACE VIEW valorant_dw.analytics_voting AS
SELECT
    v.vote_id,
    v.player_id,
    vs.skin_name,
    c.charity_name AS charity_voted,
    v.voted_at
FROM valorant_dw.votes v
JOIN valorant_dw.voting_skins vs ON v.skin_id = vs.skin_id
JOIN valorant_dw.charities c ON v.charity_id = c.charity_id;

CREATE OR REPLACE VIEW valorant_dw.analytics_donations AS
SELECT
    p.purchase_id,
    p.player_id AS buyer_id,
    vs.skin_name,
    c.charity_name AS beneficiary,
    p.amount_vp,
    p.purchased_at
FROM valorant_dw.purchases p
JOIN valorant_dw.voting_skins vs ON p.skin_id = vs.skin_id
JOIN valorant_dw.charities c ON p.charity_id = c.charity_id;
