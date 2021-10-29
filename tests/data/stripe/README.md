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
