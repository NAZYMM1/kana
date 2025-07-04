-- Анализ логистических операций Lancaster Group
-- SQL запросы для исследования данных

-- ================================================================
-- 1. ОБЩАЯ СТАТИСТИКА ПО ПОСТАВКАМ
-- ================================================================

-- Общая статистика по статусам поставок
SELECT 
    status,
    COUNT(*) as shipment_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM shipments
GROUP BY status
ORDER BY shipment_count DESC;

-- Статистика по месяцам
SELECT 
    DATE_TRUNC('month', ship_date) as month,
    COUNT(*) as total_shipments,
    COUNT(CASE WHEN status = 'Задержка' THEN 1 END) as delayed_shipments,
    ROUND(COUNT(CASE WHEN status = 'Задержка' THEN 1 END) * 100.0 / COUNT(*), 2) as delay_rate
FROM shipments
GROUP BY DATE_TRUNC('month', ship_date)
ORDER BY month;

-- ================================================================
-- 2. АНАЛИЗ МАРШРУТОВ С НАИБОЛЬШИМИ ЗАТРАТАМИ И ЗАДЕРЖКАМИ
-- ================================================================

-- ТОП-10 самых дорогих маршрутов с высокими задержками
WITH route_stats AS (
    SELECT 
        r.route_id,
        r.start_point,
        r.end_point,
        r.distance_km,
        r.avg_cost_rub,
        r.avg_time_hours,
        COUNT(s.shipment_id) as shipment_count,
        AVG(EXTRACT(EPOCH FROM (s.actual_delivery - s.planned_delivery))/3600) as avg_delay_hours,
        AVG(s.delivery_cost) as actual_avg_cost
    FROM routes r
    LEFT JOIN shipments s ON r.route_id = s.route_id
    GROUP BY r.route_id, r.start_point, r.end_point, r.distance_km, r.avg_cost_rub, r.avg_time_hours
)
SELECT 
    route_id,
    start_point || ' → ' || end_point as route,
    distance_km,
    ROUND(actual_avg_cost, 2) as avg_delivery_cost,
    ROUND(avg_delay_hours, 2) as avg_delay_hours,
    shipment_count,
    ROUND(actual_avg_cost / distance_km, 2) as cost_per_km
FROM route_stats
WHERE avg_delay_hours > 6 AND shipment_count > 5
ORDER BY actual_avg_cost DESC, avg_delay_hours DESC
LIMIT 10;

-- ================================================================
-- 3. РЕЙТИНГ НЕНАДЕЖНЫХ ПЕРЕВОЗЧИКОВ
-- ================================================================

-- Рейтинг перевозчиков по количеству просроченных доставок
WITH carrier_performance AS (
    SELECT 
        c.carrier_id,
        c.name,
        c.avg_rating,
        c.reliability_score,
        COUNT(s.shipment_id) as total_shipments,
        COUNT(CASE WHEN s.status = 'Задержка' THEN 1 END) as delayed_shipments,
        AVG(EXTRACT(EPOCH FROM (s.actual_delivery - s.planned_delivery))/3600) as avg_delay_hours,
        AVG(s.delivery_cost) as avg_cost
    FROM carriers c
    LEFT JOIN shipments s ON c.carrier_id = s.carrier_id
    GROUP BY c.carrier_id, c.name, c.avg_rating, c.reliability_score
)
SELECT 
    carrier_id,
    name,
    total_shipments,
    delayed_shipments,
    ROUND(delayed_shipments * 100.0 / total_shipments, 2) as delay_rate_percent,
    ROUND(avg_delay_hours, 2) as avg_delay_hours,
    ROUND(avg_cost, 2) as avg_delivery_cost,
    avg_rating,
    reliability_score,
    -- Расчет индекса эффективности
    ROUND(
        (reliability_score * avg_rating) / 
        (COALESCE(delayed_shipments * 100.0 / total_shipments, 0) + 1), 
        3
    ) as efficiency_index
FROM carrier_performance
WHERE total_shipments > 10
ORDER BY delay_rate_percent DESC, avg_delay_hours DESC;

-- ================================================================
-- 4. СРАВНЕНИЕ ПОКАЗАТЕЛЕЙ ДОСТАВКИ ПО РЕГИОНАМ
-- ================================================================

-- Анализ производительности по регионам (на основе начальных и конечных точек)
WITH regional_stats AS (
    SELECT 
        r.start_point as region,
        'Отправление' as direction,
        COUNT(s.shipment_id) as shipment_count,
        AVG(EXTRACT(EPOCH FROM (s.actual_delivery - s.planned_delivery))/3600) as avg_delay_hours,
        AVG(s.delivery_cost) as avg_cost,
        COUNT(CASE WHEN s.status = 'Задержка' THEN 1 END) as delayed_count
    FROM routes r
    JOIN shipments s ON r.route_id = s.route_id
    GROUP BY r.start_point
    
    UNION ALL
    
    SELECT 
        r.end_point as region,
        'Прибытие' as direction,
        COUNT(s.shipment_id) as shipment_count,
        AVG(EXTRACT(EPOCH FROM (s.actual_delivery - s.planned_delivery))/3600) as avg_delay_hours,
        AVG(s.delivery_cost) as avg_cost,
        COUNT(CASE WHEN s.status = 'Задержка' THEN 1 END) as delayed_count
    FROM routes r
    JOIN shipments s ON r.route_id = s.route_id
    GROUP BY r.end_point
)
SELECT 
    region,
    SUM(shipment_count) as total_shipments,
    ROUND(AVG(avg_delay_hours), 2) as avg_delay_hours,
    ROUND(AVG(avg_cost), 2) as avg_delivery_cost,
    SUM(delayed_count) as total_delayed,
    ROUND(SUM(delayed_count) * 100.0 / SUM(shipment_count), 2) as delay_rate_percent
FROM regional_stats
GROUP BY region
HAVING SUM(shipment_count) > 20
ORDER BY delay_rate_percent DESC;

-- ================================================================
-- 5. АНАЛИЗ ВРЕМЕННЫХ ПАТТЕРНОВ ЗАДЕРЖЕК
-- ================================================================

-- Анализ задержек по дням недели
SELECT 
    EXTRACT(DOW FROM ship_date) as day_of_week,
    CASE EXTRACT(DOW FROM ship_date)
        WHEN 0 THEN 'Воскресенье'
        WHEN 1 THEN 'Понедельник'
        WHEN 2 THEN 'Вторник'
        WHEN 3 THEN 'Среда'
        WHEN 4 THEN 'Четверг'
        WHEN 5 THEN 'Пятница'
        WHEN 6 THEN 'Суббота'
    END as day_name,
    COUNT(*) as total_shipments,
    COUNT(CASE WHEN status = 'Задержка' THEN 1 END) as delayed_shipments,
    ROUND(COUNT(CASE WHEN status = 'Задержка' THEN 1 END) * 100.0 / COUNT(*), 2) as delay_rate,
    ROUND(AVG(EXTRACT(EPOCH FROM (actual_delivery - planned_delivery))/3600), 2) as avg_delay_hours
FROM shipments
GROUP BY EXTRACT(DOW FROM ship_date)
ORDER BY day_of_week;

-- Анализ пиков задержек по неделям
SELECT 
    DATE_TRUNC('week', ship_date) as week_start,
    COUNT(*) as total_shipments,
    COUNT(CASE WHEN status = 'Задержка' THEN 1 END) as delayed_shipments,
    ROUND(COUNT(CASE WHEN status = 'Задержка' THEN 1 END) * 100.0 / COUNT(*), 2) as delay_rate,
    ROUND(AVG(EXTRACT(EPOCH FROM (actual_delivery - planned_delivery))/3600), 2) as avg_delay_hours
FROM shipments
GROUP BY DATE_TRUNC('week', ship_date)
HAVING COUNT(*) > 20
ORDER BY delay_rate DESC
LIMIT 10;

-- ================================================================
-- 6. АНАЛИЗ ПРИЧИН ЗАДЕРЖЕК
-- ================================================================

-- Статистика по причинам задержек
SELECT 
    d.reason,
    COUNT(*) as delay_count,
    ROUND(AVG(d.delay_hours), 2) as avg_delay_hours,
    ROUND(SUM(d.delay_hours), 2) as total_delay_hours,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM delays d
GROUP BY d.reason
ORDER BY delay_count DESC;

-- Связь причин задержек с маршрутами
SELECT 
    r.start_point || ' → ' || r.end_point as route,
    d.reason,
    COUNT(*) as delay_count,
    ROUND(AVG(d.delay_hours), 2) as avg_delay_hours
FROM delays d
JOIN routes r ON d.route_id = r.route_id
GROUP BY r.start_point, r.end_point, d.reason
HAVING COUNT(*) > 2
ORDER BY delay_count DESC, avg_delay_hours DESC;

-- ================================================================
-- 7. ЗАГРУЗКА СКЛАДОВ И РИСКИ
-- ================================================================

-- Анализ загрузки складов
SELECT 
    warehouse_id,
    region,
    capacity,
    current_load,
    utilization_rate,
    CASE 
        WHEN utilization_rate >= 0.9 THEN 'Критическая загрузка'
        WHEN utilization_rate >= 0.8 THEN 'Высокая загрузка'
        WHEN utilization_rate >= 0.6 THEN 'Средняя загрузка'
        ELSE 'Низкая загрузка'
    END as load_status,
    capacity - current_load as free_space
FROM warehouses
ORDER BY utilization_rate DESC;

-- ================================================================
-- 8. ТОПОЛОГИЯ СЕТИ И УЗКИЕ МЕСТА
-- ================================================================

-- Самые загруженные маршруты
WITH route_volume AS (
    SELECT 
        r.route_id,
        r.start_point,
        r.end_point,
        r.distance_km,
        COUNT(s.shipment_id) as shipment_volume,
        SUM(s.weight_kg) as total_weight,
        COUNT(CASE WHEN s.status = 'Задержка' THEN 1 END) as delayed_shipments,
        AVG(s.delivery_cost) as avg_cost
    FROM routes r
    LEFT JOIN shipments s ON r.route_id = s.route_id
    GROUP BY r.route_id, r.start_point, r.end_point, r.distance_km
)
SELECT 
    route_id,
    start_point || ' → ' || end_point as route,
    shipment_volume,
    ROUND(total_weight, 1) as total_weight_kg,
    delayed_shipments,
    ROUND(delayed_shipments * 100.0 / shipment_volume, 2) as delay_rate,
    ROUND(avg_cost, 2) as avg_cost,
    ROUND(total_weight / distance_km, 2) as weight_density_per_km
FROM route_volume
WHERE shipment_volume > 0
ORDER BY shipment_volume DESC, delay_rate DESC
LIMIT 15;

-- ================================================================
-- 9. ФИНАНСОВЫЙ АНАЛИЗ
-- ================================================================

-- Анализ убытков от задержек (предполагаем штраф 5% от стоимости груза за задержку)
WITH financial_impact AS (
    SELECT 
        DATE_TRUNC('month', ship_date) as month,
        COUNT(*) as total_shipments,
        COUNT(CASE WHEN status = 'Задержка' THEN 1 END) as delayed_shipments,
        SUM(cargo_value_rub) as total_cargo_value,
        SUM(delivery_cost) as total_delivery_cost,
        SUM(CASE WHEN status = 'Задержка' THEN cargo_value_rub * 0.05 ELSE 0 END) as estimated_penalties
    FROM shipments
    GROUP BY DATE_TRUNC('month', ship_date)
)
SELECT 
    month,
    total_shipments,
    delayed_shipments,
    ROUND(total_cargo_value, 2) as total_cargo_value,
    ROUND(total_delivery_cost, 2) as total_delivery_cost,
    ROUND(estimated_penalties, 2) as estimated_penalties,
    ROUND(estimated_penalties * 100.0 / total_delivery_cost, 2) as penalty_rate_percent
FROM financial_impact
ORDER BY month;

-- ================================================================
-- 10. РЕКОМЕНДАЦИИ ПО ОПТИМИЗАЦИИ
-- ================================================================

-- Маршруты для приоритетной оптимизации
CREATE OR REPLACE VIEW priority_optimization_routes AS
SELECT 
    r.route_id,
    r.start_point || ' → ' || r.end_point as route,
    COUNT(s.shipment_id) as shipment_count,
    ROUND(AVG(EXTRACT(EPOCH FROM (s.actual_delivery - s.planned_delivery))/3600), 2) as avg_delay_hours,
    ROUND(AVG(s.delivery_cost), 2) as avg_cost,
    COUNT(CASE WHEN s.status = 'Задержка' THEN 1 END) as delayed_count,
    ROUND(COUNT(CASE WHEN s.status = 'Задержка' THEN 1 END) * 100.0 / COUNT(s.shipment_id), 2) as delay_rate,
    -- Индекс приоритета оптимизации (больше = выше приоритет)
    ROUND(
        (COUNT(CASE WHEN s.status = 'Задержка' THEN 1 END) * 100.0 / COUNT(s.shipment_id)) * 
        AVG(EXTRACT(EPOCH FROM (s.actual_delivery - s.planned_delivery))/3600) * 
        LOG(COUNT(s.shipment_id)), 
        2
    ) as optimization_priority_score
FROM routes r
JOIN shipments s ON r.route_id = s.route_id
GROUP BY r.route_id, r.start_point, r.end_point
HAVING COUNT(s.shipment_id) > 5
ORDER BY optimization_priority_score DESC;

-- Использование представления для получения приоритетных маршрутов
SELECT * FROM priority_optimization_routes LIMIT 10;