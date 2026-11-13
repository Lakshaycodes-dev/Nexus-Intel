# Market Intelligence Report

Query: stripe pricing
Competitor: stripe.com
Generated: 2026-11-12 11:45:10 UTC
Mock mode: True
Sources with usable content: 4/4
Pages crawled: 4; cached: 0; failed: 0
Structured changes detected: 0

---

## Source: https://stripe.com/pricing

Status: success
Categories: pricing
Classification confidence: 1.00
Billing states captured: annual, monthly
Retrieval: playwright

### Structured intelligence

```json
{
  "pricing": {
    "target": "pricing_matrix",
    "vendor": "stripe.com",
    "source_url": "https://stripe.com/pricing",
    "currency": "USD",
    "plans": [
      {
        "name": "Starter",
        "price": 0.0,
        "price_display": "$0/mo",
        "currency": "USD",
        "billing_period": "monthly",
        "seats": 1,
        "included_features": [
          "Basic dashboard and email support"
        ],
        "notes": null
      },
      {
        "name": "Growth",
        "price": 49.0,
        "price_display": "$49/mo",
        "currency": "USD",
        "billing_period": "monthly",
        "seats": 10,
        "included_features": [
          "Advanced analytics and priority support"
        ],
        "notes": null
      },
      {
        "name": "Scale",
        "price": 199.0,
        "price_display": "$199/mo",
        "currency": "USD",
        "billing_period": "monthly",
        "seats": 50,
        "included_features": [
          "SSO, audit logs, and dedicated support"
        ],
        "notes": null
      },
      {
        "name": "Starter",
        "price": 0.0,
        "price_display": "$0/yr",
        "currency": "USD",
        "billing_period": "yearly",
        "seats": 1,
        "included_features": [
          "Basic dashboard and email support"
        ],
        "notes": null
      },
      {
        "name": "Growth",
        "price": 468.0,
        "price_display": "$468/yr",
        "currency": "USD",
        "billing_period": "yearly",
        "seats": 10,
        "included_features": [
          "Advanced analytics and priority support"
        ],
        "notes": null
      },
      {
        "name": "Scale",
        "price": 1908.0,
        "price_display": "$1,908/yr",
        "currency": "USD",
        "billing_period": "yearly",
        "seats": 50,
        "included_features": [
          "SSO, audit logs, and dedicated support"
        ],
        "notes": null
      }
    ],
    "usage_based_rates": [],
    "free_tier": {
      "available": true,
      "description": "All plans include a 14-day free trial. Enterprise: contact sales for a custom quote.",
      "limits": []
    },
    "enterprise_note": "All plans include a 14-day free trial. Enterprise: contact sales for a custom quote.",
    "missing_fields": [
      "usage_based_rates"
    ],
    "warnings": []
  },
  "features": {
    "target": "feature_comparison",
    "subject": "stripe.com",
    "source_url": "https://stripe.com/pricing",
    "categories": [],
    "missing_fields": [
      "categories"
    ],
    "warnings": [
      "no deterministic feature rows detected"
    ]
  },
  "summary": {
    "title": "Stripe Pricing",
    "source_url": "https://stripe.com/pricing",
    "summary": "Choose the plan that fits your team. Prices are billed monthly.\n\nStarter $0/mo\nBasic dashboard and email support\n\nGrowth $49/mo\nAdvanced analytics and priority support",
    "headings": [
      "Pricing",
      "Plans",
      "Compare plans"
    ],
    "product_details": [
      {
        "name": "Stripe Pricing",
        "detail": "Choose the plan that fits your team. Prices are billed monthly.\n\nStarter $0/mo\nBasic dashboard and email support\n\nGrowth $49/mo\nAdvanced analytics and priority support",
        "source_url": "https://stripe.com/pricing"
      }
    ],
    "classification": {
      "primary": "pricing",
      "categories": [
        "pricing"
      ],
      "confidence": 1.0,
      "signals": [
        "url:pricing",
        "title:Pricing",
        "heading:Pricing",
        "text:/yr",
        "text:billed annually",
        "text:free trial"
      ]
    },
    "text_length": 665
  }
}
```

### Rendered content

#### Snapshot: monthly

**Page title:** Stripe Pricing

**Meta description:** Plans and pricing for Stripe.

**Billing state:** monthly

**Retrieval method:** playwright

**Headings:** Pricing / Plans / Compare plans

Stripe Pricing

Choose the plan that fits your team. Prices are billed monthly.

Starter $0/mo
Basic dashboard and email support

Growth $49/mo
Advanced analytics and priority support

Scale $199/mo
SSO, audit logs, and dedicated support

All plans include a 14-day free trial. Enterprise: contact sales for a custom quote.

| Plan | Monthly price | Seats | Features |
| --- | --- | --- | --- |
| Starter | $0/mo | 1 | Basic dashboard and email support |
| Growth | $49/mo | 10 | Advanced analytics and priority support |
| Scale | $199/mo | 50 | SSO, audit logs, and dedicated support |

#### Snapshot: annual

**Page title:** Stripe Pricing

**Meta description:** Plans and pricing for Stripe.

**Billing state:** annual

**Retrieval method:** playwright

**Headings:** Pricing / Plans / Compare plans

Stripe Pricing

Choose the plan that fits your team. Prices are billed annually.

Starter $0/yr
Basic dashboard and email support

Growth $468/yr
Advanced analytics and priority support

Scale $1,908/yr
SSO, audit logs, and dedicated support

All annual plans include a 14-day free trial. Enterprise: contact sales for a custom quote.

| Plan | Annual price | Seats | Features |
| --- | --- | --- | --- |
| Starter | $0/yr | 1 | Basic dashboard and email support |
| Growth | $468/yr | 10 | Advanced analytics and priority support |
| Scale | $1,908/yr | 50 | SSO, audit logs, and dedicated support |

---

## Source: https://stripe.com/features

Status: success
Categories: features, product
Classification confidence: 1.00
Billing states captured: default
Retrieval: playwright

### Structured intelligence

```json
{
  "features": {
    "target": "feature_comparison",
    "subject": "stripe.com",
    "source_url": "https://stripe.com/features",
    "categories": [
      {
        "name": "Analytics",
        "features": [
          {
            "name": "Real-time dashboards",
            "support": "unknown",
            "value": null,
            "notes": null
          },
          {
            "name": "Competitor tracking",
            "support": "unknown",
            "value": null,
            "notes": null
          },
          {
            "name": "Custom alerts",
            "support": "unknown",
            "value": null,
            "notes": null
          }
        ]
      },
      {
        "name": "Security",
        "features": [
          {
            "name": "Single sign-on (SSO)",
            "support": "unknown",
            "value": null,
            "notes": null
          },
          {
            "name": "Audit logs",
            "support": "unknown",
            "value": null,
            "notes": null
          },
          {
            "name": "Role-based access control",
            "support": "unknown",
            "value": null,
            "notes": null
          }
        ]
      }
    ],
    "missing_fields": [],
    "warnings": []
  },
  "summary": {
    "title": "Stripe Features",
    "source_url": "https://stripe.com/features",
    "summary": "## Analytics\n- Real-time dashboards\n- Competitor tracking\n- Custom alerts\n## Security\n- Single sign-on (SSO)\n- Audit logs\n- Role-based access control",
    "headings": [
      "Features",
      "Analytics",
      "Security"
    ],
    "product_details": [
      {
        "name": "Stripe Features",
        "detail": "## Analytics\n- Real-time dashboards\n- Competitor tracking\n- Custom alerts\n## Security\n- Single sign-on (SSO)\n- Audit logs\n- Role-based access control",
        "source_url": "https://stripe.com/features"
      }
    ],
    "classification": {
      "primary": "features",
      "categories": [
        "features",
        "product"
      ],
      "confidence": 1.0,
      "signals": [
        "url:features",
        "title:Features",
        "heading:Features",
        "text:Features"
      ]
    },
    "text_length": 169
  }
}
```

### Extracted feature comparison

#### Analytics

| Feature | Support | Value |
| --- | --- | --- |
| Real-time dashboards | unknown |  |
| Competitor tracking | unknown |  |
| Custom alerts | unknown |  |

#### Security

| Feature | Support | Value |
| --- | --- | --- |
| Single sign-on (SSO) | unknown |  |
| Audit logs | unknown |  |
| Role-based access control | unknown |  |

### Rendered content

**Page title:** Stripe Features

**Meta description:** Product capabilities available in Stripe.

**Billing state:** default

**Retrieval method:** playwright

**Headings:** Features / Analytics / Security

Stripe Features

Analytics
- Real-time dashboards
- Competitor tracking
- Custom alerts
Security
- Single sign-on (SSO)
- Audit logs
- Role-based access control

**Analytics**

- Real-time dashboards

- Competitor tracking

- Custom alerts

**Security**

- Single sign-on (SSO)

- Audit logs

- Role-based access control

---

## Source: https://stripe.com/changelog

Status: success
Categories: changelog
Classification confidence: 1.00
Billing states captured: default
Retrieval: playwright

### Structured intelligence

```json
{
  "announcements": {
    "target": "market_news",
    "market_segment": null,
    "source_url": "https://stripe.com/changelog",
    "items": [
      {
        "title": "New analytics dashboard",
        "url": "https://stripe.com/changelog",
        "source": null,
        "published_date": "2026-10-02",
        "published_date_raw": "2026-10-02",
        "summary": "Added real-time competitor tracking and custom alerts.",
        "entities": [],
        "sentiment_hint": null
      },
      {
        "title": "Improved audit logs",
        "url": "https://stripe.com/changelog",
        "source": null,
        "published_date": "2026-08-14",
        "published_date_raw": "2026-08-14",
        "summary": "Audit log retention increased and filters were improved.",
        "entities": [],
        "sentiment_hint": null
      },
      {
        "title": "New analytics dashboard - Added real-time competitor tracking",
        "url": "https://stripe.com/changelog",
        "source": null,
        "published_date": "2026-10-02",
        "published_date_raw": "2026-10-02",
        "summary": null,
        "entities": [],
        "sentiment_hint": null
      },
      {
        "title": "Improved audit logs - retention increased",
        "url": "https://stripe.com/changelog",
        "source": null,
        "published_date": "2026-08-14",
        "published_date_raw": "2026-08-14",
        "summary": null,
        "entities": [],
        "sentiment_hint": null
      }
    ],
    "missing_fields": [],
    "warnings": []
  },
  "summary": {
    "title": "Stripe Changelog",
    "source_url": "https://stripe.com/changelog",
    "summary": "2026-10-02 New analytics dashboard\nAdded real-time competitor tracking and custom alerts.\n\n2026-08-14 Improved audit logs\nAudit log retention increased and filters were improved.",
    "headings": [
      "Changelog",
      "Recent updates"
    ],
    "product_details": [
      {
        "name": "Stripe Changelog",
        "detail": "2026-10-02 New analytics dashboard\nAdded real-time competitor tracking and custom alerts.\n\n2026-08-14 Improved audit logs\nAudit log retention increased and filters were improved.",
        "source_url": "https://stripe.com/changelog"
      }
    ],
    "classification": {
      "primary": "changelog",
      "categories": [
        "changelog"
      ],
      "confidence": 1.0,
      "signals": [
        "url:changelog",
        "title:Changelog",
        "heading:Changelog",
        "text:Changelog"
      ]
    },
    "text_length": 218
  }
}
```

### Rendered content

**Page title:** Stripe Changelog

**Meta description:** Recent product updates from Stripe.

**Billing state:** default

**Retrieval method:** playwright

**Headings:** Changelog / Recent updates

Stripe Changelog

Recent updates

2026-10-02 New analytics dashboard
Added real-time competitor tracking and custom alerts.

2026-08-14 Improved audit logs
Audit log retention increased and filters were improved.

**Recent updates**

- 2026-10-02 New analytics dashboard - Added real-time competitor tracking

- 2026-08-14 Improved audit logs - retention increased

---

## Source: https://stripe.com/about

Status: success
Categories: company
Classification confidence: 1.00
Billing states captured: default
Retrieval: playwright

### Structured intelligence

```json
{
  "summary": {
    "title": "About Stripe",
    "source_url": "https://stripe.com/about",
    "summary": "Stripe builds competitive intelligence software for product, marketing, and strategy teams.\n\nOur mission is to make market changes visible and actionable.",
    "headings": [
      "About us",
      "Our mission"
    ],
    "product_details": [
      {
        "name": "About Stripe",
        "detail": "Stripe builds competitive intelligence software for product, marketing, and strategy teams.\n\nOur mission is to make market changes visible and actionable.",
        "source_url": "https://stripe.com/about"
      }
    ],
    "classification": {
      "primary": "company",
      "categories": [
        "company"
      ],
      "confidence": 1.0,
      "signals": [
        "url:about",
        "title:About",
        "heading:About",
        "text:Our mission"
      ]
    },
    "text_length": 171
  }
}
```

### Rendered content

**Page title:** About Stripe

**Meta description:** About Stripe.

**Billing state:** default

**Retrieval method:** playwright

**Headings:** About us / Our mission

About Stripe

Stripe builds competitive intelligence software for product, marketing, and strategy teams.

Our mission is to make market changes visible and actionable.

---
