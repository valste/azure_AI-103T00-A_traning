# ------------------------------------------------------------
# Pricing and cost tracking
# ------------------------------------------------------------

import os
from dotenv import load_dotenv

# load .env variables
load_dotenv(override=True)

COST_CURRENCY = os.getenv("COST_CURRENCY", "EUR").upper()

estimated_total_cost = 0.0


def get_env_float(name, default=0.0):
    """
    Safely reads a float value from .env.
    """

    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    try:
        return float(value)
    except ValueError:
        raise ValueError(f"Invalid numeric value for {name}: {value}")


def get_fallback_price_per_second(currency_code):
    """
    Reads SORA_PRICE_PER_SECOND_<CURRENCY> from .env.

    Example:
        SORA_PRICE_PER_SECOND_EUR=0.092
        SORA_PRICE_PER_SECOND_USD=0.10
    """

    currency_code = currency_code.upper()
    env_name = f"SORA_PRICE_PER_SECOND_{currency_code}"

    price = get_env_float(env_name, default=None)

    if price is None:
        raise ValueError(
            f"{env_name} is missing from .env. " f"Add {env_name}=<price-per-second>."
        )

    return price, env_name


def get_max_total_estimated_cost(currency_code):
    """
    Reads MAX_TOTAL_ESTIMATED_COST_<CURRENCY> from .env.

    Example:
        MAX_TOTAL_ESTIMATED_COST_EUR=2.00
        MAX_TOTAL_ESTIMATED_COST_USD=2.00

    Use 0 to disable the budget check.
    """

    currency_code = currency_code.upper()
    env_name = f"MAX_TOTAL_ESTIMATED_COST_{currency_code}"

    limit = get_env_float(env_name, default=0.0)

    return limit, env_name


def get_configured_price(currency_code):
    """
    Uses your .env fallback price as the configured Sora price.

    This intentionally treats the .env price as a local estimate, not as
    guaranteed real-time billing data.
    """

    currency_code = currency_code.upper()
    price, source_env_name = get_fallback_price_per_second(currency_code)

    return price, currency_code, source_env_name


def format_money(amount, currency_code):
    """
    Formats money consistently for terminal logs.
    """

    return f"{currency_code.upper()} {amount:.4f}"


def parse_seconds(seconds):
    """
    Converts seconds to a float for cost estimation.
    """

    try:
        return float(seconds)
    except (TypeError, ValueError):
        return 0.0


# Initialize pricing from .env
sora_price_per_second, cost_currency, price_source = get_configured_price(
    COST_CURRENCY
)

max_total_estimated_cost, budget_source = get_max_total_estimated_cost(cost_currency)


def estimate_video_cost(seconds, price_per_second):
    """
    Estimate cost using billable video seconds.

    Formula:
        estimated cost = seconds * price per second
    """

    billable_seconds = parse_seconds(seconds)
    return billable_seconds * price_per_second


def log_planned_video_cost(operation, model, size, seconds, price_per_second):
    """
    Logs cost estimate before submitting the video job.
    Also checks the currency-specific safety limit.
    """

    estimated_cost = estimate_video_cost(seconds, price_per_second)
    projected_total = estimated_total_cost + estimated_cost

    print(f"\n=== Planned cost estimate: {operation} ===")
    print(f"  Model:                  {model}")
    print(f"  Size:                   {size}")
    print(f"  Billable video seconds: {parse_seconds(seconds)}")
    print(
        f"  Price per second:       {format_money(sora_price_per_second, cost_currency)}"
    )
    print(f"  Estimated job cost:     {format_money(estimated_cost, cost_currency)}")
    print(
        f"  Current total estimate: {format_money(estimated_total_cost, cost_currency)}"
    )
    print(f"  Projected total:        {format_money(projected_total, cost_currency)}")
    print(f"  Price source:           {price_source}")

    if max_total_estimated_cost > 0:
        print(
            f"  Budget limit:           {format_money(max_total_estimated_cost, cost_currency)}"
        )
        print(f"  Budget source:          {budget_source}")

        if projected_total > max_total_estimated_cost:
            raise RuntimeError(
                f"Budget limit exceeded. "
                f"Projected total {format_money(projected_total, cost_currency)} "
                f"is greater than budget limit "
                f"{format_money(max_total_estimated_cost, cost_currency)}."
            )
    else:
        print("  Budget limit:           disabled")

    print()

    return estimated_cost


def record_estimated_cost(operation, estimated_cost):
    """
    Adds the job estimate to the running total after the video request is submitted.
    """

    global estimated_total_cost

    estimated_total_cost += estimated_cost

    print(f"=== Cost recorded: {operation} ===")
    print(f"  Estimated job cost:  {format_money(estimated_cost, cost_currency)}")
    print(f"  Cumulative estimate: {format_money(estimated_total_cost, cost_currency)}")
    print()




#####-------------------------------------------------------------
# get current pricing and budget from azure 
####

import requests


def get_current_price_for_model_usage_per_second(model="Sora-2", currency="EUR"):
    """
    Retrieve the current public listed Azure retail price per generated second
    for a model such as Sora-2 in the requested currency.

    Args:
        model: Model name to search for, for example "Sora-2", "Sora 2", or "sora-2".
        currency: ISO currency code supported by the Azure Retail Prices API,
                  for example "EUR" or "USD".

    Returns:
        dict:
            {
                "model": "Sora-2",
                "price_per_second": 0.092,
                "currency": "EUR",
                "unit": "...",
                "service_name": "...",
                "product_name": "...",
                "sku_name": "...",
                "meter_name": "...",
                "region": "...",
                "source": "Azure Retail Prices API",
                "raw_item": {...}
            }

    Raises:
        RuntimeError if no matching per-second model price is found.
    """

    currency = currency.upper()
    model_search = model.lower().replace("-", " ").strip()

    base_url = "https://prices.azure.com/api/retail/prices"

    candidate_filters = [
        "serviceName eq 'Azure OpenAI' and contains(meterName, 'Sora')",
        "serviceName eq 'Azure OpenAI Service' and contains(meterName, 'Sora')",
        "serviceName eq 'Cognitive Services' and contains(meterName, 'Sora')",
        "contains(productName, 'Sora')",
        "contains(meterName, 'Sora')",
        "contains(skuName, 'Sora')",
    ]

    all_candidates = []

    for filter_expression in candidate_filters:
        params = {
            "api-version": "2023-01-01-preview",
            "currencyCode": currency,
            "$filter": filter_expression,
        }

        url = base_url

        while url:
            response = requests.get(
                url,
                params=params if url == base_url else None,
                timeout=30,
            )
            response.raise_for_status()

            payload = response.json()
            all_candidates.extend(payload.get("Items", []))

            url = payload.get("NextPageLink")
            params = None

        if all_candidates:
            break

    def normalize(value):
        return str(value or "").lower().replace("-", " ")

    def searchable_text(item):
        fields = [
            "serviceName",
            "productName",
            "skuName",
            "meterName",
            "unitOfMeasure",
            "armSkuName",
            "type",
            "priceType",
        ]
        return " ".join(normalize(item.get(field)) for field in fields)

    matching_items = []

    for item in all_candidates:
        text = searchable_text(item)

        model_matches = model_search in text

        unit = normalize(item.get("unitOfMeasure"))
        meter = normalize(item.get("meterName"))

        per_second = (
            "second" in unit
            or "second" in meter
            or "sec" in unit
            or "sec" in meter
        )

        price_type = normalize(item.get("priceType") or item.get("type"))
        is_consumption = (
            price_type == ""
            or price_type == "consumption"
            or "consumption" in price_type
        )

        if model_matches and per_second and is_consumption:
            matching_items.append(item)

    if not matching_items:
        raise RuntimeError(
            f"No current public per-second price found for model '{model}' "
            f"in currency '{currency}'. The Azure Retail Prices API meter names "
            "may have changed, or the model price may not be published there yet."
        )

    def score(item):
        text = searchable_text(item)
        value = 0

        if model_search in text:
            value += 100

        if "global" in text:
            value += 20

        if "second" in text:
            value += 20

        if "720" in text or "1280" in text:
            value += 10

        if normalize(item.get("priceType")) == "consumption":
            value += 10

        return value

    best = sorted(matching_items, key=score, reverse=True)[0]

    price = best.get("retailPrice")
    if price is None:
        price = best.get("unitPrice")

    if price is None:
        raise RuntimeError(
            f"A matching price item was found for '{model}', "
            "but it did not contain retailPrice or unitPrice."
        )

    returned_currency = best.get("currencyCode", currency)

    return {
        "model": model,
        "price_per_second": float(price),
        "currency": returned_currency,
        "unit": best.get("unitOfMeasure"),
        "service_name": best.get("serviceName"),
        "product_name": best.get("productName"),
        "sku_name": best.get("skuName"),
        "meter_name": best.get("meterName"),
        "region": best.get("armRegionName"),
        "source": "Azure Retail Prices API",
        "raw_item": best,
    }
    
#####------current price from Azure Retail Prices API
print("#####------current price from Azure Retail Prices API")
price_info = get_current_price_for_model_usage_per_second(
    model="Sora-2",
    currency="EUR",
)

print("Current listed model usage price:")
print(f"  Model:  {price_info['model']}")
print(
    f"  Price:  {price_info['currency']} "
    f"{price_info['price_per_second']:.4f} per second"
)
print(f"  Meter:  {price_info['meter_name']}")
print(f"  SKU:    {price_info['sku_name']}")
print(f"  Unit:   {price_info['unit']}")
print(f"  Source: {price_info['source']}")
    

#####----------------.env configured price and budget summary  
print("#####----------------.env configured price and budget summary  ")

print(f"Cost currency: {cost_currency}")
print(
    f"Configured price per second: {format_money(sora_price_per_second, cost_currency)}"
)
print(f"Price source: {price_source}")

if max_total_estimated_cost > 0:
    print(f"Budget limit: {format_money(max_total_estimated_cost, cost_currency)}")
    print(f"Budget source: {budget_source}")
else:
    print("Budget limit: disabled")
