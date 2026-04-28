"""Auto-generated tool module."""

from __future__ import annotations

import json


def run(payload: str) -> str:
    import json
    import math
    from datetime import datetime, date, timedelta

    try:
        data = json.loads(payload)
        settlement = datetime.strptime(data["settlement_date"], "%Y-%m-%d").date()
        maturity = datetime.strptime(data["maturity_date"], "%Y-%m-%d").date()
        coupon_rate = data["coupon_rate"]
        frequency = data["frequency"]
        face_value = data["face_value"]
        convention = data.get("day_count_convention", "30/360")

        if settlement >= maturity:
            return json.dumps({"error": "Settlement date must be before maturity date"}, ensure_ascii=False)
        if coupon_rate <= 0:
            return json.dumps({"error": "Coupon rate must be positive"}, ensure_ascii=False)
        if face_value <= 0:
            return json.dumps({"error": "Face value must be positive"}, ensure_ascii=False)

        months_between = 12 // frequency
        coupon_payment = face_value * coupon_rate / frequency

        # Generate payment dates from settlement to maturity
        payment_dates = []
        current = maturity
        while current >= settlement:
            payment_dates.append(current)
            month = current.month - months_between
            year = current.year
            if month <= 0:
                month += 12
                year -= 1
            import calendar
            max_day = calendar.monthrange(year, month)[1]
            day = min(current.day, max_day)
            current = date(year, month, day)

        payment_dates.sort()
        # Remove dates before settlement (keep first one after settlement for accrual)
        payment_dates = [d for d in payment_dates if d > settlement]
        if not payment_dates:
            return json.dumps({"error": "No remaining payments before maturity"}, ensure_ascii=False)

        # Calculate days between last coupon date (or settlement) and next coupon
        # For simplicity, use actual/365 for day count in accrual
        prev_payment = settlement
        next_payment = payment_dates[0]
        days_in_period = (next_payment - prev_payment).days
        if days_in_period <= 0:
            accrued_interest = 0.0
        else:
            # find the previous coupon date before settlement
            # We'll just use the period from last payment (if exists) or issue date assumption
            # For simplicity, assume last coupon was 6 months before next payment
            estimated_last_coupon = date(
                next_payment.year - (12 // frequency) // 12,
                next_payment.month - (12 // frequency) % 12,
                next_payment.day
            )
            # adjust if negative month
            if estimated_last_coupon.month <= 0:
                estimated_last_coupon = date(estimated_last_coupon.year - 1, estimated_last_coupon.month + 12, estimated_last_coupon.day)
            days_since_last = (settlement - estimated_last_coupon).days
            if days_since_last < 0:
                days_since_last = 0
            total_days_in_period = (next_payment - estimated_last_coupon).days
            if total_days_in_period <= 0:
                accrued_interest = 0.0
            else:
                accrued_interest = coupon_payment * (days_since_last / total_days_in_period)

        # Remaining payments schedule
        schedule = []
        for pmt_date in payment_dates:
            schedule.append({
                "payment_date": pmt_date.isoformat(),
                "coupon_amount": round(coupon_payment, 2)
            })

        # Yield to maturity approximation using Newton's method (simplified)
        # We'll just estimate using current price = par value for simplicity
        remaining_cashflows = [coupon_payment] * (len(payment_dates) - 1) + [coupon_payment + face_value]
        # guess ytm = coupon_rate
        ytm = coupon_rate
        for _ in range(100):
            price = 0.0
            t = 0
            for i, cf in enumerate(remaining_cashflows):
                t = (payment_dates[i] - settlement).days / 365.0
                price += cf / ((1 + ytm/frequency)**(t*frequency))
            diff = price - face_value
            if abs(diff) < 1e-6:
                break
            # derivative
            deriv = 0.0
            for i, cf in enumerate(remaining_cashflows):
                t = (payment_dates[i] - settlement).days / 365.0
                deriv += -cf * t / (frequency * (1 + ytm/frequency)**(t*frequency + 1))
            if deriv == 0:
                break
            ytm -= diff / deriv
            if ytm < 0:
                ytm = 0.01

        result = {
            "next_payment_date": payment_dates[0].isoformat(),
            "number_of_remaining_payments": len(payment_dates),
            "accrued_interest": round(accrued_interest, 2),
            "coupon_payment_per_period": round(coupon_payment, 2),
            "payment_schedule": schedule,
            "yield_to_maturity_estimate": round(ytm, 6),
            "total_remaining_coupons": round(coupon_payment * len(payment_dates), 2)
        }
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return f'error: {e}'


TOOL_SPEC = {
    "name": "bond_coupon_payment_calculator",
    "description": "Calculate remaining coupon payments and accrued interest for a fixed-rate bond given its maturity date, coupon rate, payment frequency, and settlement date. Returns payment schedule, next payment date, accrued interest, and yield-to-maturity estimate.",
    "category": "operations",
    "domain": "finance",
    "risk_level": "read",
    "schema": {
    "type": "object",
    "properties": {
        "settlement_date": {
            "type": "string",
            "description": "Date when bond trade settles, format YYYY-MM-DD"
        },
        "maturity_date": {
            "type": "string",
            "description": "Date when bond principal is repaid, format YYYY-MM-DD"
        },
        "coupon_rate": {
            "type": "number",
            "description": "Annual coupon rate as a decimal (e.g. 0.05 for 5%)"
        },
        "frequency": {
            "type": "integer",
            "description": "Number of coupon payments per year (1=annual, 2=semi-annual, 4=quarterly)",
            "enum": [
                1,
                2,
                4
            ]
        },
        "face_value": {
            "type": "number",
            "description": "Par value of the bond in currency units"
        },
        "day_count_convention": {
            "type": "string",
            "description": "Optional: Day count convention for interest calculation. Default is '30/360'.",
            "enum": [
                "30/360",
                "actual/360",
                "actual/365",
                "actual/actual"
            ],
            "default": "30/360"
        }
    },
    "required": [
        "settlement_date",
        "maturity_date",
        "coupon_rate",
        "frequency",
        "face_value"
    ]
},
}
