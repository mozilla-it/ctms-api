# Stripe test data

These files represent full Stripe objects, like those returned from the Stripe
API or cached in the Firefox Accounts (FxA) Firestore instance. All were taken
from the test servers, used by Mozilla employees to QA the subscription
platform. IDs and other identifying features in the data have been changed to
generic equivalents.

## Customers

The [Customer object](https://stripe.com/docs/api/customers/object) sample files:

* [customer_01.json](./customer_01.json) - A customer with a default payment
  method.


## Subscriptions

The [Subscription object](https://stripe.com/docs/api/subscriptions/object) sample files:

* [subscription_01.json](./subscription_01.json) - An active subscription. This includes
  the `plan` member, an FxA addition that duplicates some of the `price` data.


## Invoice

The [Invoice object](https://stripe.com/docs/api/invoices/object) sample files:

* [invoice_01.json](./invoice_01.json) - An invoice for a daily subscription. This
  includes the `plan` member, an FxA addition that duplicates some of the `price` data.
