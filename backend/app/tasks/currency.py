import requests
from datetime import datetime
from sqlmodel import Session
from app.tasks import celery
from app.db.session import SessionLocal
from app.models.currency import CurrencyRate

@celery.task(name="fetch_currency_rates")
def fetch_currency_rates():
    """
    Fetch currency exchange rates from the Exchange Rates API and store them in the database.
    Using the free API from exchangerate-api.com
    """
    # Create database session
    db = SessionLocal()
    try:
        # Base currency (free API only supports USD as base)
        base_currency = "USD"
        target_currencies = ["EUR", "GBP", "JPY", "AUD", "CAD"]
        
        # Fetch exchange rates
        response = requests.get(f"https://open.er-api.com/v6/latest/{base_currency}")
        data = response.json()
        
        if response.status_code == 200 and data.get("rates"):
            rates = data["rates"]
            current_time = datetime.utcnow()
            
            # Store rates in database
            for target in target_currencies:
                if target in rates:
                    rate = CurrencyRate(
                        base_currency=base_currency,
                        target_currency=target,
                        rate=rates[target],
                        timestamp=current_time
                    )
                    db.add(rate)
            
            db.commit()
            return {"status": "success", "message": "Currency rates updated successfully"}
        
        return {"status": "error", "message": "Failed to fetch currency rates"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
    finally:
        db.close()

# Schedule the task to run every hour
@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        3600.0,  # 1 hour in seconds
        fetch_currency_rates.s(),
        name='fetch-currency-rates-hourly'
    ) 