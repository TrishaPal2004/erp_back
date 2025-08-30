import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class FreshBitesDataGenerator:
    def __init__(self):
        self.skus = ['SKU001_Snacks', 'SKU002_Beverages', 'SKU003_Cheese', 'SKU004_Bakery', 'SKU005_Frozen']
        self.dcs = ['Mumbai', 'Kolkata']
        self.suppliers = ['SUP001', 'SUP002', 'SUP003', 'SUP004', 'SUP005']
        self.weeks = 104  # 2 years
        self.festival_weeks = [8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 96]  # 12 festivals/year
        self.plant_capacity = 10000
        
        # SKU characteristics
        self.sku_multipliers = {
            'SKU001_Snacks': 1.2,
            'SKU002_Beverages': 1.0,
            'SKU003_Cheese': 0.8,
            'SKU004_Bakery': 1.1,
            'SKU005_Frozen': 0.9
        }
    
    def generate_base_demand(self, week, sku):
        """Generate base demand with seasonality"""
        seasonality = 1 + 0.3 * np.sin((week * 2 * np.pi) / 52)  # Annual seasonality
        weekly_pattern = 1 + 0.1 * np.sin((week * 2 * np.pi) / 4)  # Monthly pattern
        base_demand = 500 * self.sku_multipliers[sku] * seasonality * weekly_pattern
        noise = (np.random.random() - 0.5) * 100
        return max(50, base_demand + noise)
    
    def generate_forecast_data(self):
        """Generate forecast.csv data"""
        data = []
        for week in range(1, self.weeks + 1):
            for sku in self.skus:
                for dc in self.dcs:
                    base_demand = self.generate_base_demand(week, sku)
                    is_festival = week in self.festival_weeks
                    festival_uplift = (0.4 + np.random.random() * 0.1) if is_festival else 0
                    
                    forecast_qty = int(base_demand * (1 + festival_uplift))
                    
                    data.append({
                        'week': week,
                        'sku': sku,
                        'dc': dc,
                        'forecast_qty': forecast_qty,
                        'festival_flag': 1 if is_festival else 0
                    })
        
        return pd.DataFrame(data)
    
    def generate_actuals_data(self, forecast_df):
        """Generate actuals.csv data based on forecast with noise"""
        actuals = []
        for _, row in forecast_df.iterrows():
            variance = 0.3 if row['festival_flag'] else 0.15
            noise = (np.random.random() - 0.5) * 2 * variance
            actual_qty = int(max(0, row['forecast_qty'] * (1 + noise)))
            
            # City bias: Mumbai higher variance, Kolkata more stable
            if row['dc'] == 'Mumbai':
                actual_qty = int(actual_qty * (0.95 + np.random.random() * 0.1))
            else:  # Kolkata
                actual_qty = int(actual_qty * (1.0 + np.random.random() * 0.05))
            
            actuals.append({
                'week': row['week'],
                'sku': row['sku'],
                'dc': row['dc'],
                'actual_qty': actual_qty
            })
        
        return pd.DataFrame(actuals)
    
    def generate_inventory_data(self):
        """Generate inventory.csv data"""
        data = []
        for sku in self.skus:
            plant_onhand = int(1000 + np.random.random() * 2000)
            mumbai_onhand = int(300 + np.random.random() * 700)
            kolkata_onhand = int(500 + np.random.random() * 1000)  # Kolkata tends to have more
            expiry_date = datetime.now() + timedelta(days=np.random.randint(10, 20))  # e.g., expires between 1 month to 1 year
            days_remaining = (expiry_date - datetime.now()).days
            data.append({
                'week0': 0,
                'sku': sku,
                'plant_onhand': plant_onhand,
                'mumbai_onhand': mumbai_onhand,
                'kolkata_onhand': kolkata_onhand,
                'days_remaining': days_remaining
            })
        
        return pd.DataFrame(data)
    
    def generate_capacity_data(self):
        """Generate capacity.csv data"""
        data = []
        for week in range(1, self.weeks + 1):
            capacity = int(self.plant_capacity * (0.9 + np.random.random() * 0.2))
            data.append({
                'week': week,
                'plant_capacity_units': capacity
            })
        
        return pd.DataFrame(data)
    
    def generate_suppliers_data(self):
        """Generate suppliers.csv data"""
        data = []
        for i, supplier_id in enumerate(self.suppliers):
            sku = self.skus[i]  # Each supplier maps to one SKU
            data.append({
                'supplier_id': supplier_id,
                'sku': sku,
                'avg_lead_time_wk': 2 + np.random.random() * 3,  # 2-5 weeks
                'lead_time_std': 0.5 + np.random.random() * 1,   # 0.5-1.5 weeks std
                'on_time_prob': 0.7 + np.random.random() * 0.25  # 70-95%
            })
        
        return pd.DataFrame(data)
    
    def generate_deliveries_data(self, suppliers_df):
        """Generate deliveries.csv data"""
        data = []
        for week in range(1, self.weeks - 5):  # Stop 5 weeks before end
            for _, supplier in suppliers_df.iterrows():
                if np.random.random() < 0.6:  # 60% chance of delivery each week
                    lead_time = max(1, int(supplier['avg_lead_time_wk'] + 
                                         (np.random.random() - 0.5) * supplier['lead_time_std'] * 2))
                    arrival_week = week + lead_time
                    
                    if arrival_week <= self.weeks:
                        data.append({
                            'week_release': week,
                            'week_arrival': arrival_week,
                            'sku': supplier['sku'],
                            'qty': int(200 + np.random.random() * 800),  # 200-1000 units
                            'supplier_id': supplier['supplier_id']
                        })
        
        return pd.DataFrame(data)
    
    def calculate_baseline_forecast(self, actuals_df):
        """Calculate baseline forecast performance"""
        baseline_data = []
        performance_data = []
        
        for week in range(5, self.weeks + 1):
            for sku in self.skus:
                for dc in self.dcs:
                    # Get last 4 weeks of actuals
                    last_four = actuals_df[
                        (actuals_df['week'] >= week - 4) & 
                        (actuals_df['week'] < week) & 
                        (actuals_df['sku'] == sku) & 
                        (actuals_df['dc'] == dc)
                    ]['actual_qty']
                    
                    if len(last_four) >= 4:
                        naive_baseline = last_four.mean()
                        
                        # Add festival uplift
                        is_festival = week in self.festival_weeks
                        festival_adjusted = naive_baseline * (1.45 if is_festival else 1)
                        
                        actual_value = actuals_df[
                            (actuals_df['week'] == week) & 
                            (actuals_df['sku'] == sku) & 
                            (actuals_df['dc'] == dc)
                        ]['actual_qty'].iloc[0]
                        
                        baseline_data.append({
                            'week': week,
                            'sku': sku,
                            'dc': dc,
                            'naive_forecast': int(naive_baseline),
                            'festival_adjusted_forecast': int(festival_adjusted),
                            'actual': actual_value
                        })
                        
                        # Calculate MAPE
                        naive_mape = abs(actual_value - naive_baseline) / actual_value
                        festival_mape = abs(actual_value - festival_adjusted) / actual_value
                        
                        performance_data.append({
                            'week': week,
                            'sku': sku,
                            'dc': dc,
                            'naive_mape': naive_mape,
                            'festival_mape': festival_mape,
                            'is_festival': is_festival
                        })
        
        return pd.DataFrame(baseline_data), pd.DataFrame(performance_data)
    
    def generate_all_data(self, save_to_csv=True):
        """Generate all datasets"""
        print("Generating FreshBites Supply Chain Data...")
        
        # Generate all datasets
        forecast_df = self.generate_forecast_data()
        actuals_df = self.generate_actuals_data(forecast_df)
        inventory_df = self.generate_inventory_data()
        capacity_df = self.generate_capacity_data()
        suppliers_df = self.generate_suppliers_data()
        deliveries_df = self.generate_deliveries_data(suppliers_df)
        baseline_df, performance_df = self.calculate_baseline_forecast(actuals_df)
        
        datasets = {
            'forecast': forecast_df,
            'actuals': actuals_df,
            'inventory': inventory_df,
            'capacity': capacity_df,
            'suppliers': suppliers_df,
            'deliveries': deliveries_df,
            'baseline_forecast': baseline_df,
            'performance': performance_df
        }
        
        if save_to_csv:
            for name, df in datasets.items():
                filename = f"{name}.csv"
                df.to_csv(filename, index=False)
                print(f"✅ Generated {filename} with {len(df):,} records")
        
        return datasets
    
    def plot_eda(self, datasets):
        """Generate EDA plots"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('FreshBites Supply Chain - Exploratory Data Analysis', fontsize=16)
        
        # 1. Demand patterns by DC
        weekly_demand = datasets['actuals'].groupby(['week', 'dc'])['actual_qty'].sum().reset_index()
        weekly_pivot = weekly_demand.pivot(index='week', columns='dc', values='actual_qty')
        
        axes[0, 0].plot(weekly_pivot.index[:52], weekly_pivot['Mumbai'][:52], label='Mumbai', color='red', alpha=0.7)
        axes[0, 0].plot(weekly_pivot.index[:52], weekly_pivot['Kolkata'][:52], label='Kolkata', color='blue', alpha=0.7)
        axes[0, 0].set_title('Weekly Demand by DC (Year 1)')
        axes[0, 0].set_xlabel('Week')
        axes[0, 0].set_ylabel('Total Demand')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. Festival impact
        festival_comparison = datasets['actuals'].copy()
        festival_comparison['is_festival'] = festival_comparison['week'].isin(self.festival_weeks)
        festival_avg = festival_comparison.groupby(['sku', 'is_festival'])['actual_qty'].mean().reset_index()
        festival_pivot = festival_avg.pivot(index='sku', columns='is_festival', values='actual_qty')
        
        festival_pivot.plot(kind='bar', ax=axes[0, 1], color=['skyblue', 'orange'])
        axes[0, 1].set_title('Average Demand: Normal vs Festival Weeks')
        axes[0, 1].set_xlabel('SKU')
        axes[0, 1].set_ylabel('Average Demand')
        axes[0, 1].legend(['Normal', 'Festival'])
        axes[0, 1].tick_params(axis='x', rotation=45)
        
        # 3. Forecast accuracy
        weekly_mape = datasets['performance'].groupby('week')[['naive_mape', 'festival_mape']].mean()
        
        axes[1, 0].plot(weekly_mape.index[:52], weekly_mape['naive_mape'][:52] * 100, 
                       label='Naive MAPE', color='red', alpha=0.7)
        axes[1, 0].plot(weekly_mape.index[:52], weekly_mape['festival_mape'][:52] * 100, 
                       label='Festival-Adjusted MAPE', color='green', alpha=0.7)
        axes[1, 0].set_title('Forecast Accuracy Over Time (Year 1)')
        axes[1, 0].set_xlabel('Week')
        axes[1, 0].set_ylabel('MAPE (%)')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. Supplier reliability
        supplier_performance = datasets['deliveries'].copy()
        supplier_performance['is_late'] = supplier_performance['week_arrival'] > supplier_performance['week_release'] + 3
        late_deliveries = supplier_performance.groupby('supplier_id')['is_late'].mean()
        
        late_deliveries.plot(kind='bar', ax=axes[1, 1], color='coral')
        axes[1, 1].set_title('Supplier Late Delivery Rate')
        axes[1, 1].set_xlabel('Supplier ID')
        axes[1, 1].set_ylabel('Late Delivery Rate')
        axes[1, 1].tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.savefig('freshbites_eda.png', dpi=300, bbox_inches='tight')
        plt.show()
        
        # Print summary statistics
        print("\n" + "="*50)
        print("DATASET SUMMARY")
        print("="*50)
        
        total_demand = datasets['actuals']['actual_qty'].sum()
        avg_weekly_demand = datasets['actuals'].groupby('week')['actual_qty'].sum().mean()
        
        print(f"📊 Total demand (2 years): {total_demand:,} units")
        print(f"📈 Average weekly demand: {avg_weekly_demand:,.0f} units")
        
        festival_uplift = datasets['actuals'][datasets['actuals']['week'].isin(self.festival_weeks)]['actual_qty'].mean()
        normal_demand = datasets['actuals'][~datasets['actuals']['week'].isin(self.festival_weeks)]['actual_qty'].mean()
        uplift_pct = (festival_uplift - normal_demand) / normal_demand * 100
        
        print(f"🎉 Festival demand uplift: {uplift_pct:.1f}%")
        
        mumbai_var = datasets['actuals'][datasets['actuals']['dc'] == 'Mumbai']['actual_qty'].std()
        kolkata_var = datasets['actuals'][datasets['actuals']['dc'] == 'Kolkata']['actual_qty'].std()
        
        print(f"📍 Mumbai demand std: {mumbai_var:.0f}")
        print(f"📍 Kolkata demand std: {kolkata_var:.0f}")
        print(f"📍 Mumbai vs Kolkata variance ratio: {mumbai_var/kolkata_var:.2f}x")
        
        avg_mape_naive = datasets['performance']['naive_mape'].mean() * 100
        avg_mape_festival = datasets['performance']['festival_mape'].mean() * 100
        
        print(f"🎯 Naive forecast MAPE: {avg_mape_naive:.1f}%")
        print(f"🎯 Festival-adjusted MAPE: {avg_mape_festival:.1f}%")
        print(f"🎯 Forecast improvement: {avg_mape_naive - avg_mape_festival:.1f} percentage points")

# Usage
if __name__ == "__main__":
    generator = FreshBitesDataGenerator()
    datasets = generator.generate_all_data(save_to_csv=True)
    generator.plot_eda(datasets)
    
    print("\n🎉 Data generation complete! Files saved:")
    print("   • forecast.csv, actuals.csv, inventory.csv")
    print("   • capacity.csv, suppliers.csv, deliveries.csv")
    print("   • baseline_forecast.csv, performance.csv")
    print("   • freshbites_eda.png (visualization)")