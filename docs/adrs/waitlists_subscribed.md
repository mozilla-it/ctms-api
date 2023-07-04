# Waitlists `subscribed` field

* Status: accepted
* Deciders: <CTMS stakeholders>
* Date: June 29, 2023

## Context and Problem Statement

Since #492, onboarding new waitlists does not require any code change, redeploy, etc.

The waitlists data sent by Basket is stored without any intervention on the CMTS side.

For the Basket service, waitlists are a specific kind of newsletter. For this reason, in order to remove a user from a waitlist, Basket will mimic what is done for newsletters and send the field `"subscribed": false` and an optional `unsub_reason` text field.

We currently don't store these incoming fields in the database, and we just use the flag to delete existing waitlist records when set to `false`.

For the synchronization of waitlists to Acoustic (#561), we have to implement this waitlist unsubscription situation.


## Decision Drivers

In order to choose our solution we considered the following criteria:

- **Complexity**: Low → High: how complex is the solution
- **Cost**: Low → High: Low → High: how much engineering efforts is required
- **Robustness**: Low → High: how reliable is the solution
- **Adaptability**: Low → High: capacity to adjust and conform to the business requirements


## Considered Options

1. [Option 1 - Add subscribed field](#option-1---add-subscribed-field)
2. [Option 2 - Reset before add](#option-2---reset-before-add)
3. [Option 3 - Fetch and compare](#option-3--fetch-and-compare)
4. [Option 4 - Implement deletion queue](#option-4---implement-deletion-queue)

## Decision Outcome

Chosen option: *Option 1* because it is most pragmatic decision. And it has the best ratio complexity/robustness. Although it does not match entirely the waiting list concept, it will be understood by stakeholders since it follows Basket. It is indeed a missed opportunity to revamp the synchronization process using a queue, but it should be reasonably easy to migrate both newsletters and waitlists together when the time comes.

## Pros and Cons of the Options

### Option 1 - Add subscribed field

This solution consists in adding the `subscribed : boolean` field to the waitlist table in the database, and turn it to `false` when Basket does. The `unsub_reason` text field holds an optional text.

This is also known as *soft deletion*.

**Complexity**: Low

This mimics what currently exists for newsletters.

**Cost**: Mid

The change was implemented in CTMS in a matter of hours in pull-request #707.

The cost is *Mid* and not *Low*, because it requires a tiny change in Basket to be implemented and deployed (filter the waitlist objects with `subscribed=true` in CTMS responses), and thus requires some coordination efforts.

In parallel, if we look at possible evolutions of the synchronization code of CTMS, like the synchronization queue presented in *Option 4*, we could consider it regrettable to mimic newsletters. However, this evolution is not officially planned yet, and may never happen. Plus, since it will be the exact same approach as for newsletters, migrating both together to the new solution won't represent much additional effort, compared to just migrating newsletters.

**Robustness**: High

When synchronizing with Acoustic, we would simply delete waitlists entries where `subscribed` is `false`. It does not affect existing waitlists entries where `subscribed` is `true`. The operation is idempotent and can be interrupted and retried without impact.
If we want to store the `subscribed` column in Acoustic, like we plan to do for newsletters in #562, we just upsert all entries.

**Adaptability**: Low

We introduce this notion as a consequence of Basket modelling, and it may skew the concepts manipulated by stakeholders when querying Acoustic.

Conceptually, the notion of unsubscription for a waitlist isn't really adequate. Users join and may leave waiting lists. They don't really "subscribe" to a waitlist.
Although members of the waitlist may receive announcements of product availability or be invited to join a newsletter, waitlists are not implicitly turned into newsletters from which users have to unsubscribe.

### Option 2 - Reset before add

Since we don't delete waitlists when we receive unsubscription, we loose track of their previous state in CTMS, and can't determine which have to be deleted in Acoustic. In order to keep both sides in sync, we could delete all records in Acoustic, and re-add all records present in CTMS.

**Complexity**: Low

The Acoustic has endpoints to delete relational tables by key, and the resulting code should not be too complex.

**Cost**: Mid

Would require to use Acoustic API endpoints that are not currently used in CTMS.

**Robustness**: Low

This approach is fragile, because it would require at least two API calls.
It would double the amount of requests sent to Acoustic, and will slow down synchronization.
And it won't be transactional: if the deletion step works, but the addition part can never go through, we loose all records on the Acoustic side.

**Adaptability**: Mid

Acoustic just lists the users's waitlists. This matches reality and stakeholders notions.

With this solution, the text with the unsubscribe reason isn't stored in CTMS nor Acoustic (although the form on the Basket would show it).

### Option 3 - Fetch and compare

Same as *Option 2*, except that we would fetch what is store on Acoustic to determine which entries have to be deleted.

**Complexity**: Low

More or less equivalent as *Option 2*, adding a trivial comparison step.

**Cost**: Mid

Same as *Option 2*, it would require to use Acoustic API endpoints that are not currently used in CTMS.

**Robustness**: Mid

This approach is robust in terms of data integrity. We are not exposed to TOCTOU issues since the data synchronization occurs from a single process. And other entities manipulating Acoustic are not likely to modify waitlists entries.

It would double the amount of requests sent to Acoustic, and will slow down synchronization. Which makes the system less robust. Hence *Mid* instead of *High* on this criteria.

**Adaptability**: Mid

Acoustic just lists the users's waitlists. This matches reality and stakeholders notions.

With this solution, the text with the unsubscribe reason isn't stored in CTMS nor Acoustic (although the form on the Basket would show it).

### Option 4 - Implement deletion queue

For this solution, we implement a deletion queue, as described in #571.

When Basket sends an unsubscription to CTMS, we delete the record from the CTMS database, and store an entry in a synchronization queue. Like for example:

```
operation: delete
tablename: waitlist
key: {"email_id": "F9601A02-09C0-4C38-9C61-DC8F9F3CB79F", "name": "vpn"}
```

During the synchronization process, we process this queue, and remove entries from it, only if the deletion was successful on the Acoustic side.

Note: If the text with the unsubscribe reason would have to be stored in CTMS and Acoustic, we would combine this with *Option 1*, and store an `update` operation in the synchronization queue.

**Complexity**: Mid

The concept is simple. But until this solution is applied to all kind of records (contact, newsletters, etc.), and the old one completely removed, this adds up to the current complexity of the code base.

**Cost**: High

This is a whole project in itself.

**Robustness**: High

The additions and removals from the queue are transactional with the reception and emission of Basket and Acoustic requests. The operations in the queue can be retried until success.

**Adaptability**: High

Acoustic just lists the users's waitlists. This matches reality and stakeholders notions.

Combining with soft-deletion and storing the unsubscribe reason is possible if necessary, and does not fundamentally change the design.
