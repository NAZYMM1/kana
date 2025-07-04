import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# Настройка стиля для matplotlib
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class LogisticsAnalyzer:
    """Класс для анализа логистических данных"""
    
    def __init__(self, data_path='data/'):
        """Инициализация с загрузкой данных"""
        self.data_path = data_path
        self.shipments = None
        self.routes = None
        self.carriers = None
        self.warehouses = None
        self.delays = None
        
    def load_data(self):
        """Загрузка всех датасетов"""
        try:
            self.shipments = pd.read_csv(f'{self.data_path}shipments.csv')
            self.routes = pd.read_csv(f'{self.data_path}routes.csv')
            self.carriers = pd.read_csv(f'{self.data_path}carriers.csv')
            self.warehouses = pd.read_csv(f'{self.data_path}warehouses.csv')
            self.delays = pd.read_csv(f'{self.data_path}delays.csv')
            
            # Преобразование дат
            self.shipments['ship_date'] = pd.to_datetime(self.shipments['ship_date'])
            self.shipments['planned_delivery'] = pd.to_datetime(self.shipments['planned_delivery'])
            self.shipments['actual_delivery'] = pd.to_datetime(self.shipments['actual_delivery'])
            self.delays['date'] = pd.to_datetime(self.delays['date'])
            
            print("Данные успешно загружены!")
            return True
            
        except Exception as e:
            print(f"Ошибка при загрузке данных: {e}")
            return False
    
    def get_data_summary(self):
        """Получение сводной информации о данных"""
        if self.shipments is None:
            print("Сначала загрузите данные с помощью load_data()")
            return
        
        summary = {
            'Общее количество поставок': len(self.shipments),
            'Количество маршрутов': len(self.routes),
            'Количество перевозчиков': len(self.carriers),
            'Количество складов': len(self.warehouses),
            'Количество зафиксированных задержек': len(self.delays),
            'Доля задержанных поставок': f"{(self.shipments['status'] == 'Задержка').mean():.1%}",
            'Период анализа': f"{self.shipments['ship_date'].min().date()} - {self.shipments['ship_date'].max().date()}"
        }
        
        return summary
    
    def calculate_delivery_metrics(self):
        """Расчет метрик доставки"""
        # Добавляем колонку с фактической длительностью доставки
        self.shipments['actual_duration_hours'] = (
            self.shipments['actual_delivery'] - pd.to_datetime(self.shipments['ship_date'])
        ).dt.total_seconds() / 3600
        
        # Добавляем колонку с задержкой
        self.shipments['delay_hours'] = (
            self.shipments['actual_delivery'] - self.shipments['planned_delivery']
        ).dt.total_seconds() / 3600
        
        # Заполняем отрицательные задержки нулями (доставка раньше срока)
        self.shipments['delay_hours'] = self.shipments['delay_hours'].clip(lower=0)
        
        return self.shipments
    
    def plot_delivery_time_distribution(self):
        """График распределения времени доставки"""
        if 'actual_duration_hours' not in self.shipments.columns:
            self.calculate_delivery_metrics()
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Анализ времени доставки', fontsize=16, fontweight='bold')
        
        # Гистограмма времени доставки
        axes[0,0].hist(self.shipments['actual_duration_hours'], bins=50, alpha=0.7, color='skyblue')
        axes[0,0].set_title('Распределение времени доставки')
        axes[0,0].set_xlabel('Часы')
        axes[0,0].set_ylabel('Количество поставок')
        
        # Boxplot задержек по статусу
        status_data = [
            self.shipments[self.shipments['status'] == 'Доставлено']['delay_hours'],
            self.shipments[self.shipments['status'] == 'Задержка']['delay_hours']
        ]
        axes[0,1].boxplot(status_data, labels=['Доставлено', 'Задержка'])
        axes[0,1].set_title('Задержки по статусу доставки')
        axes[0,1].set_ylabel('Часы задержки')
        
        # Временной ряд задержек
        daily_delays = self.shipments.groupby('ship_date')['delay_hours'].mean()
        axes[1,0].plot(daily_delays.index, daily_delays.values, alpha=0.7)
        axes[1,0].set_title('Средние задержки по дням')
        axes[1,0].set_xlabel('Дата')
        axes[1,0].set_ylabel('Средняя задержка (часы)')
        axes[1,0].tick_params(axis='x', rotation=45)
        
        # Задержки по дням недели
        self.shipments['weekday'] = self.shipments['ship_date'].dt.day_name()
        weekday_delays = self.shipments.groupby('weekday')['delay_hours'].mean()
        weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        weekday_delays = weekday_delays.reindex(weekday_order)
        
        axes[1,1].bar(range(len(weekday_delays)), weekday_delays.values, color='lightcoral')
        axes[1,1].set_title('Средние задержки по дням недели')
        axes[1,1].set_xlabel('День недели')
        axes[1,1].set_ylabel('Средняя задержка (часы)')
        axes[1,1].set_xticks(range(len(weekday_delays)))
        axes[1,1].set_xticklabels(['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'])
        
        plt.tight_layout()
        plt.savefig('visualizations/delivery_time_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
    
    def analyze_routes_efficiency(self):
        """Анализ эффективности маршрутов"""
        # Объединяем данные о поставках и маршрутах
        shipments_routes = self.shipments.merge(self.routes, on='route_id')
        
        # Группируем по маршрутам
        route_metrics = shipments_routes.groupby('route_id').agg({
            'delay_hours': ['mean', 'count'],
            'delivery_cost': 'mean',
            'avg_time_hours': 'first',
            'distance_km': 'first',
            'start_point': 'first',
            'end_point': 'first'
        }).round(2)
        
        # Упрощаем названия колонок
        route_metrics.columns = ['avg_delay', 'shipment_count', 'avg_cost', 'planned_time', 'distance', 'start', 'end']
        
        # Добавляем эффективность (обратная величина к задержке * стоимость)
        route_metrics['efficiency_score'] = 1 / (route_metrics['avg_delay'] + 1) / (route_metrics['avg_cost'] / 1000)
        
        return route_metrics
    
    def plot_route_efficiency(self):
        """Интерактивная визуализация эффективности маршрутов"""
        route_metrics = self.analyze_routes_efficiency()
        
        # Создаем интерактивный scatter plot
        fig = px.scatter(
            route_metrics, 
            x='avg_cost', 
            y='avg_delay',
            size='shipment_count',
            color='efficiency_score',
            hover_data=['distance', 'planned_time'],
            title='Анализ эффективности маршрутов',
            labels={
                'avg_cost': 'Средняя стоимость доставки (руб)',
                'avg_delay': 'Средняя задержка (часы)',
                'shipment_count': 'Количество поставок',
                'efficiency_score': 'Индекс эффективности'
            },
            color_continuous_scale='RdYlGn'
        )
        
        fig.update_layout(
            width=800,
            height=600,
            showlegend=True
        )
        
        fig.write_html('visualizations/route_efficiency_interactive.html')
        fig.show()
        
        return route_metrics
    
    def analyze_carriers_performance(self):
        """Анализ производительности перевозчиков"""
        # Объединяем данные
        shipments_carriers = self.shipments.merge(self.carriers, on='carrier_id')
        
        # Группируем по перевозчикам
        carrier_metrics = shipments_carriers.groupby(['carrier_id', 'name']).agg({
            'delay_hours': 'mean',
            'delivery_cost': 'mean',
            'shipment_id': 'count',
            'avg_rating': 'first',
            'reliability_score': 'first'
        }).round(2)
        
        carrier_metrics.columns = ['avg_delay', 'avg_cost', 'total_shipments', 'rating', 'reliability']
        
        # Вычисляем долю задержанных поставок
        delayed_by_carrier = shipments_carriers[shipments_carriers['status'] == 'Задержка'].groupby('carrier_id').size()
        total_by_carrier = shipments_carriers.groupby('carrier_id').size()
        delay_rate = (delayed_by_carrier / total_by_carrier * 100).fillna(0)
        
        carrier_metrics['delay_rate_percent'] = delay_rate
        
        return carrier_metrics.reset_index()
    
    def plot_carriers_comparison(self):
        """Сравнение перевозчиков"""
        carrier_metrics = self.analyze_carriers_performance()
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Анализ производительности перевозчиков', fontsize=16, fontweight='bold')
        
        # Средние задержки
        top_carriers = carrier_metrics.nlargest(10, 'total_shipments')
        axes[0,0].barh(top_carriers['name'], top_carriers['avg_delay'], color='lightcoral')
        axes[0,0].set_title('Средние задержки по перевозчикам (ТОП-10 по объему)')
        axes[0,0].set_xlabel('Средняя задержка (часы)')
        
        # Соотношение надежности и стоимости
        axes[0,1].scatter(carrier_metrics['avg_cost'], carrier_metrics['reliability'], 
                         s=carrier_metrics['total_shipments']/10, alpha=0.6, color='skyblue')
        axes[0,1].set_xlabel('Средняя стоимость доставки (руб)')
        axes[0,1].set_ylabel('Индекс надежности')
        axes[0,1].set_title('Надежность vs Стоимость')
        
        # Доля задержанных поставок
        axes[1,0].bar(range(len(top_carriers)), top_carriers['delay_rate_percent'], color='orange')
        axes[1,0].set_title('Доля задержанных поставок (%)')
        axes[1,0].set_xlabel('Перевозчики')
        axes[1,0].set_ylabel('Процент задержек')
        axes[1,0].set_xticks(range(len(top_carriers)))
        axes[1,0].set_xticklabels(top_carriers['name'], rotation=45, ha='right')
        
        # Рейтинг vs реальная производительность
        axes[1,1].scatter(carrier_metrics['rating'], carrier_metrics['avg_delay'], 
                         s=carrier_metrics['total_shipments']/10, alpha=0.6, color='lightgreen')
        axes[1,1].set_xlabel('Рейтинг перевозчика')
        axes[1,1].set_ylabel('Средняя задержка (часы)')
        axes[1,1].set_title('Рейтинг vs Фактические задержки')
        
        plt.tight_layout()
        plt.savefig('visualizations/carriers_performance.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        return carrier_metrics
    
    def analyze_warehouse_utilization(self):
        """Анализ загрузки складов"""
        # Создаем интерактивную визуализацию загрузки складов
        fig = px.bar(
            self.warehouses.sort_values('utilization_rate', ascending=False),
            x='region',
            y='utilization_rate',
            color='utilization_rate',
            title='Загрузка складов по регионам',
            labels={'utilization_rate': 'Уровень загрузки', 'region': 'Регион'},
            color_continuous_scale='RdYlGn_r'
        )
        
        # Добавляем линию критической загрузки (85%)
        fig.add_hline(y=0.85, line_dash="dash", line_color="red", 
                     annotation_text="Критический уровень (85%)")
        
        fig.update_layout(xaxis_tickangle=-45)
        fig.write_html('visualizations/warehouse_utilization.html')
        fig.show()
        
        # Находим склады с критической загрузкой
        critical_warehouses = self.warehouses[self.warehouses['utilization_rate'] > 0.85]
        
        return critical_warehouses
    
    def cluster_routes(self, n_clusters=3):
        """Кластеризация маршрутов по эффективности"""
        route_metrics = self.analyze_routes_efficiency()
        
        # Подготавливаем данные для кластеризации
        features = ['avg_delay', 'avg_cost', 'distance', 'planned_time']
        X = route_metrics[features].fillna(0)
        
        # Стандартизируем данные
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Применяем KMeans
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        route_metrics['cluster'] = kmeans.fit_predict(X_scaled)
        
        # Создаем интерактивную 3D визуализацию
        fig = px.scatter_3d(
            route_metrics, 
            x='avg_cost', 
            y='avg_delay', 
            z='distance',
            color='cluster',
            size='shipment_count',
            hover_data=['planned_time'],
            title='Кластеризация маршрутов',
            labels={
                'avg_cost': 'Средняя стоимость',
                'avg_delay': 'Средняя задержка',
                'distance': 'Расстояние'
            }
        )
        
        fig.write_html('visualizations/route_clustering.html')
        fig.show()
        
        # Анализируем характеристики кластеров
        cluster_summary = route_metrics.groupby('cluster')[features].mean().round(2)
        cluster_summary['routes_count'] = route_metrics.groupby('cluster').size()
        
        return route_metrics, cluster_summary
    
    def generate_recommendations(self):
        """Генерация рекомендаций на основе анализа"""
        recommendations = []
        
        # Анализ перевозчиков
        carrier_metrics = self.analyze_carriers_performance()
        worst_carriers = carrier_metrics.nlargest(3, 'delay_rate_percent')
        
        recommendations.append("🚛 ПЕРЕВОЗЧИКИ:")
        for _, carrier in worst_carriers.iterrows():
            recommendations.append(
                f"- Заменить '{carrier['name']}' (задержки: {carrier['delay_rate_percent']:.1f}%, "
                f"средняя задержка: {carrier['avg_delay']:.1f} ч)"
            )
        
        # Анализ складов
        critical_warehouses = self.analyze_warehouse_utilization()
        recommendations.append("\n📦 СКЛАДЫ:")
        if len(critical_warehouses) > 0:
            for _, warehouse in critical_warehouses.iterrows():
                recommendations.append(
                    f"- Склад в {warehouse['region']}: загрузка {warehouse['utilization_rate']:.1%} "
                    f"({warehouse['current_load']}/{warehouse['capacity']} единиц)"
                )
        else:
            recommendations.append("- Все склады работают в нормальном режиме")
        
        # Анализ маршрутов
        route_metrics = self.analyze_routes_efficiency()
        problematic_routes = route_metrics[
            (route_metrics['avg_delay'] > route_metrics['avg_delay'].quantile(0.8)) &
            (route_metrics['avg_cost'] > route_metrics['avg_cost'].quantile(0.8))
        ]
        
        recommendations.append("\n🛣️ МАРШРУТЫ:")
        recommendations.append(f"- {len(problematic_routes)} маршрутов требуют оптимизации")
        recommendations.append(f"- {(len(problematic_routes)/len(route_metrics)*100):.1f}% маршрутов дают значительную долю задержек")
        
        return "\n".join(recommendations)

def create_analysis_report(analyzer):
    """Создание полного отчета по анализу"""
    report = []
    
    # Заголовок
    report.append("# ОТЧЕТ ПО АНАЛИЗУ ЛОГИСТИЧЕСКИХ ОПЕРАЦИЙ LANCASTER GROUP")
    report.append("=" * 60)
    
    # Сводная информация
    summary = analyzer.get_data_summary()
    report.append("\n## 📊 СВОДНАЯ ИНФОРМАЦИЯ")
    for key, value in summary.items():
        report.append(f"- {key}: {value}")
    
    # Рекомендации
    recommendations = analyzer.generate_recommendations()
    report.append(f"\n## ✅ РЕКОМЕНДАЦИИ\n{recommendations}")
    
    # Сохраняем отчет
    with open('visualizations/analysis_report.txt', 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
    
    return "\n".join(report)