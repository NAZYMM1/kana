import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

# Устанавливаем seed для воспроизводимости
np.random.seed(42)
random.seed(42)

def generate_carriers():
    """Генерирует данные о перевозчиках"""
    carriers = [
        "TransLog Express", "RussiaCargo", "LogiMaster", "DeliveryPro", "CargoFast",
        "TransService", "ExpressWay", "CargoLink", "LogiTrans", "QuickShip",
        "MegaCargo", "SpeedyTrans", "ReliableCargo", "FastTrack", "CargoExpert"
    ]
    
    data = []
    for i, name in enumerate(carriers, 1):
        data.append({
            'carrier_id': i,
            'name': name,
            'avg_rating': round(np.random.normal(4.2, 0.8), 1),
            'fleet_size': np.random.randint(10, 150),
            'reliability_score': round(np.random.uniform(0.7, 0.98), 2)
        })
    
    return pd.DataFrame(data)

def generate_warehouses():
    """Генерирует данные о складах"""
    regions = ["Москва", "СПБ", "Екатеринбург", "Новосибирск", "Казань", "Нижний Новгород", 
               "Челябинск", "Ростов-на-Дону", "Уфа", "Волгоград", "Пермь", "Воронеж"]
    
    data = []
    for i, region in enumerate(regions, 1):
        capacity = np.random.randint(1000, 5000)
        # Некоторые склады специально делаем перегруженными
        if i in [3, 7, 9]:  # 3 склада с высокой загрузкой
            current_load = int(capacity * np.random.uniform(0.85, 0.95))
        else:
            current_load = int(capacity * np.random.uniform(0.4, 0.8))
            
        data.append({
            'warehouse_id': i,
            'region': region,
            'capacity': capacity,
            'current_load': current_load,
            'utilization_rate': round(current_load / capacity, 2)
        })
    
    return pd.DataFrame(data)

def generate_routes():
    """Генерирует данные о маршрутах"""
    cities = ["Москва", "СПБ", "Екатеринбург", "Новосибирск", "Казань", "Нижний Новгород", 
              "Челябинск", "Ростов-на-Дону", "Уфа", "Волгоград", "Пермь", "Воронеж"]
    
    data = []
    route_id = 1
    
    for start_city in cities:
        for end_city in cities:
            if start_city != end_city:
                # Базовое расстояние (условные единицы)
                base_distance = np.random.randint(200, 2000)
                
                # Время в пути зависит от расстояния с некоторой вариативностью
                avg_time = base_distance / np.random.uniform(40, 80) + np.random.uniform(2, 12)
                
                # Стоимость зависит от расстояния и времени
                avg_cost = base_distance * np.random.uniform(15, 35) + avg_time * np.random.uniform(500, 1500)
                
                data.append({
                    'route_id': route_id,
                    'start_point': start_city,
                    'end_point': end_city,
                    'distance_km': base_distance,
                    'avg_time_hours': round(avg_time, 1),
                    'avg_cost_rub': round(avg_cost, 2)
                })
                route_id += 1
    
    return pd.DataFrame(data)

def generate_shipments(routes_df, carriers_df, warehouses_df, num_shipments=5000):
    """Генерирует данные о грузоперевозках"""
    data = []
    
    # Временной диапазон: последние 6 месяцев
    start_date = datetime.now() - timedelta(days=180)
    
    for i in range(1, num_shipments + 1):
        route = routes_df.sample(1).iloc[0]
        carrier = carriers_df.sample(1).iloc[0]
        
        # Дата отправки
        ship_date = start_date + timedelta(days=np.random.randint(0, 180))
        
        # Плановое время доставки
        planned_hours = route['avg_time_hours'] + np.random.uniform(-2, 6)
        planned_delivery = ship_date + timedelta(hours=planned_hours)
        
        # Фактическое время доставки (с учетом задержек)
        delay_factor = 1 - carrier['reliability_score']
        if np.random.random() < delay_factor:
            # Есть задержка
            delay_hours = np.random.exponential(8)
            actual_delivery = planned_delivery + timedelta(hours=delay_hours)
            status = "Задержка" if delay_hours > 4 else "Доставлено"
        else:
            # Доставка в срок или раньше
            actual_delivery = planned_delivery + timedelta(hours=np.random.uniform(-1, 1))
            status = "Доставлено"
        
        # Вес и стоимость груза
        weight = np.random.uniform(100, 5000)
        cargo_value = weight * np.random.uniform(500, 3000)
        
        data.append({
            'shipment_id': i,
            'ship_date': ship_date.strftime('%Y-%m-%d'),
            'planned_delivery': planned_delivery.strftime('%Y-%m-%d %H:%M'),
            'actual_delivery': actual_delivery.strftime('%Y-%m-%d %H:%M'),
            'weight_kg': round(weight, 1),
            'cargo_value_rub': round(cargo_value, 2),
            'sender': f"Отправитель_{np.random.randint(1, 100)}",
            'receiver': f"Получатель_{np.random.randint(1, 100)}",
            'route_id': route['route_id'],
            'carrier_id': carrier['carrier_id'],
            'status': status,
            'delivery_cost': round(route['avg_cost_rub'] * np.random.uniform(0.8, 1.2), 2)
        })
    
    return pd.DataFrame(data)

def generate_delays(routes_df, shipments_df):
    """Генерирует данные о задержках"""
    delay_reasons = [
        "Пробки на дорогах", "Поломка транспорта", "Плохая погода", 
        "Проблемы на таможне", "Перегрузка склада", "Нехватка водителей",
        "Технические работы", "ДТП на маршруте", "Забастовка", "Карантинные меры"
    ]
    
    data = []
    delay_id = 1
    
    # Получаем только задержанные поставки
    delayed_shipments = shipments_df[shipments_df['status'] == 'Задержка']
    
    for _, shipment in delayed_shipments.iterrows():
        planned = pd.to_datetime(shipment['planned_delivery'])
        actual = pd.to_datetime(shipment['actual_delivery'])
        delay_hours = (actual - planned).total_seconds() / 3600
        
        if delay_hours > 1:  # Записываем только значимые задержки
            data.append({
                'delay_id': delay_id,
                'route_id': shipment['route_id'],
                'date': shipment['ship_date'],
                'reason': np.random.choice(delay_reasons),
                'delay_hours': round(delay_hours, 1),
                'shipment_id': shipment['shipment_id']
            })
            delay_id += 1
    
    return pd.DataFrame(data)

def main():
    """Основная функция для генерации всех датасетов"""
    print("Генерация синтетических данных для анализа логистики Lancaster Group...")
    
    # Создаем директорию data если не существует
    os.makedirs('data', exist_ok=True)
    
    # Генерируем данные
    print("Генерация данных о перевозчиках...")
    carriers_df = generate_carriers()
    carriers_df.to_csv('data/carriers.csv', index=False, encoding='utf-8')
    
    print("Генерация данных о складах...")
    warehouses_df = generate_warehouses()
    warehouses_df.to_csv('data/warehouses.csv', index=False, encoding='utf-8')
    
    print("Генерация данных о маршрутах...")
    routes_df = generate_routes()
    routes_df.to_csv('data/routes.csv', index=False, encoding='utf-8')
    
    print("Генерация данных о грузоперевозках...")
    shipments_df = generate_shipments(routes_df, carriers_df, warehouses_df)
    shipments_df.to_csv('data/shipments.csv', index=False, encoding='utf-8')
    
    print("Генерация данных о задержках...")
    delays_df = generate_delays(routes_df, shipments_df)
    delays_df.to_csv('data/delays.csv', index=False, encoding='utf-8')
    
    print(f"\nГенерация завершена! Создано:")
    print(f"- carriers.csv: {len(carriers_df)} записей")
    print(f"- warehouses.csv: {len(warehouses_df)} записей")
    print(f"- routes.csv: {len(routes_df)} записей")
    print(f"- shipments.csv: {len(shipments_df)} записей")
    print(f"- delays.csv: {len(delays_df)} записей")
    
    # Выводим краткую статистику
    print(f"\n📊 Краткая статистика:")
    print(f"- Доля задержанных поставок: {(shipments_df['status'] == 'Задержка').mean():.1%}")
    print(f"- Средняя утилизация складов: {warehouses_df['utilization_rate'].mean():.1%}")
    print(f"- Склады с загрузкой >85%: {(warehouses_df['utilization_rate'] > 0.85).sum()}")

if __name__ == "__main__":
    main()