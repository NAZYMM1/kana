#!/usr/bin/env python3
"""
Lancaster Group Logistics Efficiency Analysis
Final Report Generator with Optimization Recommendations
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

def load_and_prepare_data():
    """Load and prepare all logistics data"""
    # Load datasets
    shipments = pd.read_csv('./data/shipments.csv')
    routes = pd.read_csv('./data/routes.csv')
    carriers = pd.read_csv('./data/carriers.csv') 
    warehouses = pd.read_csv('./data/warehouses.csv')
    delays = pd.read_csv('./data/delays.csv')
    
    # Convert dates
    shipments['ship_date'] = pd.to_datetime(shipments['ship_date'])
    shipments['planned_delivery'] = pd.to_datetime(shipments['planned_delivery'])
    shipments['actual_delivery'] = pd.to_datetime(shipments['actual_delivery'])
    
    # Calculate delay metrics
    shipments['delay_hours'] = (shipments['actual_delivery'] - shipments['planned_delivery']).dt.total_seconds() / 3600
    shipments['delay_hours'] = shipments['delay_hours'].clip(lower=0)
    shipments['delivery_days'] = (shipments['actual_delivery'] - shipments['ship_date']).dt.days
    
    return shipments, routes, carriers, warehouses, delays

def analyze_route_efficiency(shipments, routes):
    """Analyze route efficiency and identify problematic routes"""
    shipments_routes = shipments.merge(routes, on='route_id')
    
    route_metrics = shipments_routes.groupby('route_id').agg({
        'delay_hours': ['mean', 'count', 'max'],
        'delivery_cost': 'mean',
        'distance_km': 'first',
        'start_point': 'first',
        'end_point': 'first',
        'avg_time_hours': 'first'
    }).round(2)
    
    # Flatten column names
    route_metrics.columns = ['avg_delay', 'shipment_count', 'max_delay', 'avg_cost', 'distance', 'start', 'end', 'planned_time']
    route_metrics['cost_per_km'] = route_metrics['avg_cost'] / route_metrics['distance']
    route_metrics['efficiency_score'] = route_metrics['shipment_count'] / (route_metrics['avg_delay'] + 1)
    
    # Identify problematic routes
    problematic_routes = route_metrics[
        (route_metrics['avg_delay'] > route_metrics['avg_delay'].quantile(0.8)) |
        (route_metrics['cost_per_km'] > route_metrics['cost_per_km'].quantile(0.8))
    ]
    
    return route_metrics, problematic_routes

def analyze_carrier_performance(shipments, carriers):
    """Analyze carrier performance and reliability"""
    shipments_carriers = shipments.merge(carriers, on='carrier_id')
    
    carrier_metrics = shipments_carriers.groupby('carrier_id').agg({
        'delay_hours': 'mean',
        'delivery_cost': 'mean',
        'shipment_id': 'count',
        'name': 'first',
        'avg_rating': 'first',
        'reliability_score': 'first'
    }).round(2)
    
    # Calculate delay rate
    delayed_by_carrier = shipments_carriers[shipments_carriers['status'] == 'Задержка'].groupby('carrier_id').size()
    total_by_carrier = shipments_carriers.groupby('carrier_id').size()
    carrier_metrics['delay_rate'] = (delayed_by_carrier / total_by_carrier * 100).fillna(0)
    
    # Rank carriers by performance
    carrier_metrics['performance_score'] = (
        (carrier_metrics['reliability_score'] * 0.3) +
        ((100 - carrier_metrics['delay_rate']) * 0.4) +
        ((10 - carrier_metrics['delay_hours'].clip(0, 10)) * 0.3)
    )
    
    carrier_metrics = carrier_metrics.sort_values('performance_score', ascending=False)
    
    return carrier_metrics

def analyze_warehouse_utilization(warehouses):
    """Analyze warehouse utilization and capacity issues"""
    warehouses = warehouses.copy()
    warehouses['utilization_category'] = pd.cut(
        warehouses['utilization_rate'], 
        bins=[0, 0.6, 0.75, 0.85, 0.95, 1.0],
        labels=['Low', 'Normal', 'High', 'Critical', 'Overloaded']
    )
    
    critical_warehouses = warehouses[warehouses['utilization_rate'] > 0.85]
    
    return warehouses, critical_warehouses

def generate_clustering_insights(route_metrics):
    """Generate route clustering insights"""
    # Define clusters based on cost and delay quartiles
    cost_threshold = route_metrics['avg_cost'].quantile(0.75)
    delay_threshold = route_metrics['avg_delay'].quantile(0.75)
    
    conditions = [
        (route_metrics['avg_cost'] >= cost_threshold) & (route_metrics['avg_delay'] >= delay_threshold),
        (route_metrics['avg_cost'] >= cost_threshold) & (route_metrics['avg_delay'] < delay_threshold),
        (route_metrics['avg_cost'] < cost_threshold) & (route_metrics['avg_delay'] >= delay_threshold),
        (route_metrics['avg_cost'] < cost_threshold) & (route_metrics['avg_delay'] < delay_threshold)
    ]
    
    choices = ['High Cost + High Delay', 'High Cost + Low Delay', 'Low Cost + High Delay', 'Low Cost + Low Delay']
    route_metrics['cluster'] = np.select(conditions, choices, default='Other')
    
    cluster_summary = route_metrics.groupby('cluster').agg({
        'route_id': 'count',
        'avg_delay': 'mean',
        'avg_cost': 'mean',
        'shipment_count': 'sum'
    }).round(2)
    
    return route_metrics, cluster_summary

def calculate_financial_impact(shipments, carrier_metrics, critical_warehouses):
    """Calculate financial impact and potential savings"""
    # Current costs
    total_delivery_cost = shipments['delivery_cost'].sum()
    total_cargo_value = shipments['cargo_value_rub'].sum()
    
    # Delay costs (estimated)
    delay_cost_per_hour = 500  # RUB per hour of delay
    total_delay_cost = shipments['delay_hours'].sum() * delay_cost_per_hour
    
    # Potential savings from carrier optimization
    worst_carriers = carrier_metrics.tail(3)
    carrier_optimization_savings = worst_carriers['shipment_id'].sum() * worst_carriers['delay_hours'].mean() * delay_cost_per_hour
    
    # Warehouse optimization potential
    warehouse_cost_per_unit = 100  # RUB per unit per day
    warehouse_optimization_savings = sum([
        (w['current_load'] - w['capacity'] * 0.8) * warehouse_cost_per_unit * 30
        for _, w in critical_warehouses.iterrows()
        if w['current_load'] > w['capacity'] * 0.8
    ])
    
    return {
        'total_delivery_cost': total_delivery_cost,
        'total_cargo_value': total_cargo_value,
        'total_delay_cost': total_delay_cost,
        'carrier_optimization_savings': carrier_optimization_savings,
        'warehouse_optimization_savings': warehouse_optimization_savings,
        'total_potential_savings': carrier_optimization_savings + warehouse_optimization_savings
    }

def generate_recommendations(route_metrics, carrier_metrics, critical_warehouses, financial_impact):
    """Generate specific optimization recommendations"""
    recommendations = []
    
    # Route recommendations
    problematic_routes = route_metrics[route_metrics['cluster'] == 'High Cost + High Delay']
    recommendations.append(f"🛣️ ROUTE OPTIMIZATION:")
    recommendations.append(f"- Optimize {len(problematic_routes)} high-cost, high-delay routes")
    recommendations.append(f"- These routes handle {problematic_routes['shipment_count'].sum()} shipments annually")
    
    # Carrier recommendations
    worst_carriers = carrier_metrics.tail(3)
    recommendations.append(f"\n🚛 CARRIER MANAGEMENT:")
    recommendations.append("- Replace underperforming carriers:")
    for _, carrier in worst_carriers.iterrows():
        recommendations.append(f"  • {carrier['name']}: {carrier['delay_rate']:.1f}% delay rate, {carrier['shipment_id']} shipments")
    
    # Warehouse recommendations
    recommendations.append(f"\n📦 WAREHOUSE OPTIMIZATION:")
    recommendations.append(f"- {len(critical_warehouses)} warehouses need capacity management")
    for _, warehouse in critical_warehouses.iterrows():
        if warehouse['utilization_rate'] > 0.9:
            recommendations.append(f"  • {warehouse['region']}: URGENT - {warehouse['utilization_rate']:.1%} capacity")
        else:
            recommendations.append(f"  • {warehouse['region']}: Monitor - {warehouse['utilization_rate']:.1%} capacity")
    
    # Financial benefits
    recommendations.append(f"\n💰 FINANCIAL IMPACT:")
    recommendations.append(f"- Current annual delivery cost: {financial_impact['total_delivery_cost']:,.0f} RUB")
    recommendations.append(f"- Estimated delay costs: {financial_impact['total_delay_cost']:,.0f} RUB")
    recommendations.append(f"- Potential annual savings: {financial_impact['total_potential_savings']:,.0f} RUB")
    recommendations.append(f"- ROI from optimization: {(financial_impact['total_potential_savings']/financial_impact['total_delivery_cost']*100):.1f}%")
    
    return recommendations

def create_summary_dashboard(shipments, route_metrics, carrier_metrics, warehouses):
    """Create visual summary dashboard"""
    plt.style.use('seaborn-v0_8')
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Lancaster Group Logistics - Executive Summary Dashboard', fontsize=16, fontweight='bold')
    
    # 1. Delivery Performance
    status_counts = shipments['status'].value_counts()
    colors = ['#2ecc71', '#e74c3c', '#f39c12']
    axes[0,0].pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%', colors=colors)
    axes[0,0].set_title('Delivery Performance')
    
    # 2. Top 10 Routes by Volume
    top_routes = route_metrics.nlargest(10, 'shipment_count')
    axes[0,1].bar(range(len(top_routes)), top_routes['avg_delay'], color='lightcoral')
    axes[0,1].set_title('Average Delays - Top 10 Routes')
    axes[0,1].set_ylabel('Avg Delay (hours)')
    
    # 3. Carrier Performance
    top_carriers = carrier_metrics.head(10)
    axes[0,2].barh(range(len(top_carriers)), top_carriers['performance_score'], color='skyblue')
    axes[0,2].set_title('Carrier Performance Scores')
    axes[0,2].set_xlabel('Performance Score')
    
    # 4. Cost vs Delay Scatter
    scatter = axes[1,0].scatter(route_metrics['avg_cost'], route_metrics['avg_delay'], 
                               s=route_metrics['shipment_count']/5, alpha=0.6, c=route_metrics['efficiency_score'], cmap='viridis')
    axes[1,0].set_xlabel('Average Cost (RUB)')
    axes[1,0].set_ylabel('Average Delay (hours)')
    axes[1,0].set_title('Route Cost vs Delay')
    plt.colorbar(scatter, ax=axes[1,0], label='Efficiency Score')
    
    # 5. Warehouse Utilization
    warehouse_sorted = warehouses.sort_values('utilization_rate', ascending=False)
    colors_util = ['red' if x > 0.85 else 'orange' if x > 0.75 else 'green' for x in warehouse_sorted['utilization_rate']]
    axes[1,1].bar(range(len(warehouse_sorted)), warehouse_sorted['utilization_rate'], color=colors_util)
    axes[1,1].axhline(y=0.85, color='red', linestyle='--', alpha=0.7)
    axes[1,1].set_title('Warehouse Utilization')
    axes[1,1].set_ylabel('Utilization Rate')
    
    # 6. Monthly Trends
    shipments['month'] = shipments['ship_date'].dt.to_period('M')
    monthly_stats = shipments.groupby('month').agg({'shipment_id': 'count', 'delay_hours': 'mean'})
    ax6 = axes[1,2]
    ax6_twin = ax6.twinx()
    ax6.bar(range(len(monthly_stats)), monthly_stats['shipment_id'], alpha=0.7, color='lightblue')
    ax6_twin.plot(range(len(monthly_stats)), monthly_stats['delay_hours'], color='red', marker='o')
    ax6.set_title('Monthly Volume & Delays')
    ax6.set_ylabel('Shipment Count', color='blue')
    ax6_twin.set_ylabel('Avg Delay (h)', color='red')
    
    plt.tight_layout()
    plt.savefig('./visualizations/executive_summary_dashboard.png', dpi=300, bbox_inches='tight')
    return fig

def main():
    """Main analysis execution"""
    print("🏢 LANCASTER GROUP LOGISTICS EFFICIENCY ANALYSIS")
    print("="*80)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Load and prepare data
    print("📊 Loading and preparing data...")
    shipments, routes, carriers, warehouses, delays = load_and_prepare_data()
    
    # Perform analyses
    print("🔍 Analyzing route efficiency...")
    route_metrics, problematic_routes = analyze_route_efficiency(shipments, routes)
    
    print("🚛 Analyzing carrier performance...")
    carrier_metrics = analyze_carrier_performance(shipments, carriers)
    
    print("📦 Analyzing warehouse utilization...")
    warehouses_analyzed, critical_warehouses = analyze_warehouse_utilization(warehouses)
    
    print("🎯 Generating clustering insights...")
    route_metrics, cluster_summary = generate_clustering_insights(route_metrics)
    
    print("💰 Calculating financial impact...")
    financial_impact = calculate_financial_impact(shipments, carrier_metrics, critical_warehouses)
    
    # Generate summary statistics
    print("\n📈 KEY PERFORMANCE INDICATORS:")
    print("-" * 50)
    print(f"Total Shipments: {len(shipments):,}")
    print(f"Successfully Delivered: {(shipments['status'] == 'Доставлено').sum():,} ({(shipments['status'] == 'Доставлено').mean()*100:.1f}%)")
    print(f"Delayed Shipments: {(shipments['status'] == 'Задержка').sum():,} ({(shipments['status'] == 'Задержка').mean()*100:.1f}%)")
    print(f"Average Delay (when delayed): {shipments[shipments['delay_hours'] > 0]['delay_hours'].mean():.1f} hours")
    print(f"Total Delivery Cost: {financial_impact['total_delivery_cost']:,.0f} RUB")
    print(f"Cost as % of Cargo Value: {(financial_impact['total_delivery_cost']/financial_impact['total_cargo_value']*100):.2f}%")
    
    print("\n🎯 ROUTE CLUSTERING ANALYSIS:")
    print("-" * 50)
    for cluster_name, stats in cluster_summary.iterrows():
        print(f"{cluster_name}: {stats['route_id']} routes, {stats['shipment_count']} shipments")
        print(f"  → Avg delay: {stats['avg_delay']:.1f}h, Avg cost: {stats['avg_cost']:,.0f} RUB")
    
    print("\n📦 WAREHOUSE STATUS:")
    print("-" * 50)
    print(f"Average Utilization: {warehouses_analyzed['utilization_rate'].mean():.1%}")
    print(f"Warehouses >85% capacity: {len(critical_warehouses)}")
    print(f"Warehouses >90% capacity: {len(warehouses_analyzed[warehouses_analyzed['utilization_rate'] > 0.9])}")
    
    # Generate recommendations
    print("\n✅ OPTIMIZATION RECOMMENDATIONS:")
    print("=" * 50)
    recommendations = generate_recommendations(route_metrics, carrier_metrics, critical_warehouses, financial_impact)
    for rec in recommendations:
        print(rec)
    
    # Key findings based on original requirements
    print("\n🔍 KEY FINDINGS (per project requirements):")
    print("=" * 50)
    
    # Calculate the "12% routes cause 45% delays" finding
    total_delay_hours = shipments['delay_hours'].sum()
    problematic_routes_pct = len(problematic_routes) / len(route_metrics) * 100
    problematic_delay_contribution = shipments.merge(routes, on='route_id')[
        shipments.merge(routes, on='route_id')['route_id'].isin(problematic_routes.index)
    ]['delay_hours'].sum() / total_delay_hours * 100 if total_delay_hours > 0 else 0
    
    print(f"✓ {problematic_routes_pct:.0f}% of routes contribute to {problematic_delay_contribution:.0f}% of total delays")
    print(f"✓ {len(critical_warehouses)} warehouses operating at >85% capacity")
    print(f"✓ {len(carrier_metrics.tail(2))} carriers recommended for replacement")
    print(f"✓ Estimated annual savings: {financial_impact['total_potential_savings']:,.0f} RUB")
    
    # Create dashboard
    print("\n📊 Creating executive dashboard...")
    create_summary_dashboard(shipments, route_metrics, carrier_metrics, warehouses_analyzed)
    
    # Save detailed report
    report_path = './visualizations/lancaster_logistics_final_report.txt'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("LANCASTER GROUP LOGISTICS EFFICIENCY ANALYSIS - FINAL REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("EXECUTIVE SUMMARY\n")
        f.write("-" * 40 + "\n")
        f.write(f"• Total shipments analyzed: {len(shipments):,}\n")
        f.write(f"• Delivery success rate: {(shipments['status'] == 'Доставлено').mean()*100:.1f}%\n")
        f.write(f"• Routes requiring optimization: {len(problematic_routes)}\n")
        f.write(f"• Underperforming carriers: {len(carrier_metrics.tail(3))}\n")
        f.write(f"• Critical warehouse capacity issues: {len(critical_warehouses)}\n")
        f.write(f"• Potential annual savings: {financial_impact['total_potential_savings']:,.0f} RUB\n\n")
        
        f.write("DETAILED RECOMMENDATIONS\n")
        f.write("-" * 40 + "\n")
        for rec in recommendations:
            f.write(rec + "\n")
    
    print(f"\n✅ Analysis complete!")
    print(f"📄 Detailed report saved to: {report_path}")
    print(f"📊 Dashboard saved to: ./visualizations/executive_summary_dashboard.png")
    print(f"📈 Previous dashboard: ./visualizations/logistics_dashboard.png")

if __name__ == "__main__":
    main()