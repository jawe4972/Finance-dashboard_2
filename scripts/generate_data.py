import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import random

fake = Faker()

# Configuration
NUM_USERS = 10
DAYS_OF_DATA = 365 * 5  # 5 years
AVG_TRANSACTIONS_PER_DAY = 3
CATEGORIES = [
    'Food', 'Dining', 'Groceries', 'Transportation',
    'Entertainment', 'Shopping', 'Utilities', 'Rent',
    'Healthcare', 'Education', 'Other'
]

def generate_transactions():
    transactions = []
    base_date = datetime.now() - timedelta(days=DAYS_OF_DATA)
    
    for user_id in range(1, NUM_USERS + 1):
        current_date = base_date
        while current_date <= datetime.now():
            # Generate random number of transactions for this day
            num_transactions = np.random.poisson(AVG_TRANSACTIONS_PER_DAY)
            
            for _ in range(num_transactions):
                # Weekend spending patterns
                if current_date.weekday() >= 5:  # Weekend
                    amount = abs(np.random.normal(50, 30))
                else:  # Weekday
                    amount = abs(np.random.normal(30, 20))
                
                # Category-specific patterns
                category = random.choice(CATEGORIES)
                if category in ['Rent', 'Utilities']:
                    # Monthly bills
                    if current_date.day == 1:
                        amount = abs(np.random.normal(1000, 300) if category == 'Rent' 
                                  else np.random.normal(200, 50))
                    else:
                        continue
                elif category in ['Food', 'Dining', 'Groceries']:
                    # Food-related (higher on weekends)
                    if current_date.weekday() >= 5:
                        amount *= 1.5
                elif category == 'Entertainment':
                    # More likely on weekends
                    if current_date.weekday() >= 5:
                        amount *= 2
                
                transactions.append({
                    'date': current_date,
                    'amount': round(max(1, amount), 2),
                    'merchant': fake.company(),
                    'category': category,
                    'user_id': user_id,
                    'account_type': random.choice(['Checking', 'Savings', 'Credit Card'])
                })
            
            current_date += timedelta(days=1)
    
    return pd.DataFrame(transactions)

if __name__ == '__main__':
    print("Generating transaction data...")
    df = generate_transactions()
    print(f"Generated {len(df)} transactions")
    
    # Save to CSV
    df.to_csv('../data/raw/financial_transactions.csv', index=False)
    print("Data saved to ../data/raw/financial_transactions.csv")

