import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import random
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

fake = Faker()

# Configuration
NUM_USERS = 10
DAYS_OF_DATA = 365 * 5  # 5 years
AVG_TRANSACTIONS_PER_DAY = 3
CATEGORIES = [
    'Food', 'Dining', 'Groceries', 'Transportation',
    'Entertainment', 'Shopping', 'Utilities', 'Rent/Mortgage',
    'Healthcare', 'Education', 'Other', 'Income', 'Transfers'
]

def generate_transactions():
    """Generate realistic transaction data with patterns"""
    transactions = []
    base_date = datetime.now() - timedelta(days=DAYS_OF_DATA)
    
    for user_id in range(1, NUM_USERS + 1):
        current_date = base_date
        user_income = abs(np.random.normal(5000, 1500))  # Monthly income
        
        while current_date <= datetime.now():
            # Generate random number of transactions for this day
            num_transactions = np.random.poisson(AVG_TRANSACTIONS_PER_DAY)
            
            for _ in range(num_transactions):
                # Determine if this is income (paycheck) or expense
                is_income = False
                if current_date.day in [1, 15] and random.random() < 0.8:  # Paydays
                    is_income = True
                
                if is_income:
                    amount = abs(np.random.normal(user_income / 2, 200))  # Biweekly income
                    category = 'Income'
                else:
                    # Weekend spending patterns
                    if current_date.weekday() >= 5:  # Weekend
                        amount = abs(np.random.normal(50, 30))
                    else:  # Weekday
                        amount = abs(np.random.normal(30, 20))
                    
                    # Category-specific patterns
                    category = random.choice([c for c in CATEGORIES if c not in ['Income', 'Transfers']])
                    
                    if category in ['Rent/Mortgage', 'Utilities']:
                        # Monthly bills
                        if current_date.day == 1:
                            amount = abs(np.random.normal(1500, 300) if category == 'Rent/Mortgage' 
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
                        else:
                            amount *= 0.7
                    elif category == 'Shopping':
                        # Higher during holiday season
                        if current_date.month in [11, 12]:
                            amount *= 1.8
                    
                    amount = -abs(amount)  # Expenses are negative
                
                transactions.append({
                    'timestamp': current_date.strftime('%Y-%m-%d %H:%M:%S'),
                    'description': fake.bs() if not is_income else f"Salary from {fake.company()}",
                    'amount': round(amount, 2),
                    'category': category,
                    'user_id': user_id,
                    'account': random.choice(['Checking', 'Savings', 'Credit Card'])
                })
            
            current_date += timedelta(days=1)
    
    return pd.DataFrame(transactions)

if __name__ == '__main__':
    logger.info("Generating transaction data...")
    df = generate_transactions()
    logger.info(f"Generated {len(df)} transactions")
    
    # Save to CSV
    df.to_csv('../data/raw/financial_transactions.csv', index=False)
    logger.info("Data saved to ../data/raw/financial_transactions.csv")
