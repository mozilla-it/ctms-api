from uuid import uuid4

import factory

from tests.data import fake_stripe_id


class StripeCustomerDataFactory(factory.DictFactory):
    class Params:
        fxa_id = factory.LazyFunction(lambda: uuid4().hex)

    id = factory.LazyFunction(lambda: fake_stripe_id("cus", "customer"))
    object = "customer"
    address = None
    balance = 0
    created = factory.Faker("unix_time")
    currency = "usd"
    default_source = None
    delinquent = False
    description = factory.LazyAttribute(lambda o: o.fxa_id)
    discount = None
    email = factory.Faker("email")
    invoice_prefix = factory.Faker("bothify", text="###???###")
    invoice_settings = {
        "custom_fields": None,
        "default_payment_method": fake_stripe_id("pm", "payment_method"),
        "footer": None,
    }
    livemode = False
    metadata = factory.Dict({"userid": factory.SelfAttribute("..description")})
    name = factory.Faker("name")
    next_invoice_sequence = factory.Faker("pyint")
    phone = None
    preferred_locales = []
    shipping = None
    tax_exempt = "none"


__all__ = ("StripeCustomerDataFactory",)
