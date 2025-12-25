from backend.database import SessionLocal
from backend import ml_predictions
from backend.crud import get_categories

db = SessionLocal()

print("=" * 60)
print("ML SPENDING PREDICTIONS TEST")
print("=" * 60)

# Test 1: Predict overall next month spending
print("\n1. 📊 PREDICT NEXT MONTH (Overall Spending)")
print("-" * 60)
result = ml_predictions.predict_next_month_spending(db)

if 'error' in result:
    print(f"❌ {result['error']}")
else:
    print(f"💰 Predicted Amount: ${result['predicted_amount']:.2f}")
    print(f"📈 Trend: {result['trend'].upper()}")
    print(f"🎯 Confidence: {result['confidence'].upper()}")
    print(f"📊 Model Accuracy (R²): {result['model_accuracy']:.2%}")
    print(f"📉 Historical Average: ${result['historical_avg']:.2f}")
    print(f"💡 Recommendation: {result['recommendation']}")

# Test 2: Predict by category
print("\n\n2. 📊 PREDICT BY CATEGORY")
print("-" * 60)
category_predictions = ml_predictions.predict_by_category(db)

if category_predictions:
    for pred in category_predictions[:5]:  # Show top 5
        print(f"\n{pred['category_name']}:")
        print(f"  Predicted: ${pred['predicted_amount']:.2f}")
        print(f"  Trend: {pred['trend']}")
        print(f"  Confidence: {pred['confidence']}")
else:
    print("❌ No predictions available (need more data)")

# Test 3: Advanced prediction with seasonality
print("\n\n3. 🔮 ADVANCED PREDICTION (with seasonality)")
print("-" * 60)
advanced = ml_predictions.predict_spending_with_seasonality(db)

if 'error' not in advanced:
    print(f"💰 Next Month: ${advanced['predicted_next_month']:.2f}")
    print(f"📅 Next 3 Months: {[f'${x:.2f}' for x in advanced['predicted_3_months']]}")
    print(f"🎯 Confidence: {advanced['confidence'].upper()}")
    print(f"📊 Uses Seasonality: {advanced['uses_seasonality']}")

# Test 4: Budget exhaustion prediction
print("\n\n4. ⚠️  BUDGET EXHAUSTION PREDICTIONS")
print("-" * 60)

categories = get_categories(db, type='expense')
for category in categories[:3]:  # Test first 3 categories
    exhaustion = ml_predictions.predict_budget_exhaustion(db, category.id)

    print(f"\n{category.name}:")
    if 'error' in exhaustion:
        print(f"  ℹ️  {exhaustion['error']}")
    elif 'budget_status' in exhaustion and exhaustion['budget_status'] == 'exhausted':
        print(f"  ❌ {exhaustion['message']}")
    elif 'will_exceed_budget' in exhaustion:
        print(f"  💰 Budget: ${exhaustion['budget_limit']:.2f}")
        print(f"  💸 Spent: ${exhaustion['current_spending']:.2f}")
        print(f"  📉 Daily Rate: ${exhaustion['daily_spending_rate']:.2f}")
        print(f"  {exhaustion['message']}")

# Test 5: Year forecast
print("\n\n5. 📅 NEXT YEAR FORECAST")
print("-" * 60)
forecast = ml_predictions.forecast_next_year(db)

if 'error' not in forecast:
    print(f"💰 Total Predicted (12 months): ${forecast['total_predicted_spending']:.2f}")
    print(f"📊 Average Monthly: ${forecast['avg_monthly_spending']:.2f}")
    print(f"🎯 Confidence: {forecast['confidence'].upper()}")
    print(f"📈 Based on {forecast['based_on_months']} months of data")
else:
    print(f"❌ {forecast['error']}")

print("\n" + "=" * 60)
print("✅ TEST COMPLETE")
print("=" * 60)

db.close()
