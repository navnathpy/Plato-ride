# Planto-Ride activation checklist

The owner will connect backend hosting. This release removes demo inventory and implements connected scheduled-journey flows, but operating a real service requires the following work.

1. Deploy persistent single-instance API with HTTPS, backups, edge limits and monitoring. Set public API URLs in Pages and native builds.
2. Enter Cashfree API credentials securely, whitelist the domain, configure webhooks, test sandbox outcomes and reconcile payments. Complete owner-approved live transaction/refund checks before accepting customer payments.
3. Establish identity/phone checks, driver licence and vehicle/insurance/service eligibility review, Ladies eligibility verification, staff accountability, incident escalation and account recovery. Approve accounts and vehicles only after checks; the code does not perform real-world verification by itself.
4. Publish operating entity, service availability, support contact, privacy retention/deletion policy, cancellation/refund terms, pricing policy and applicable operating permissions. Arrange appropriate review for Pune service categories, including bike operations, before activation.
5. Enrol actual drivers and publish actual offers. No artificial supply is bundled. This release matches scheduled routes by exact area; automatic nearby dispatch, route-based quotes, push notifications and background GPS remain future integrations.
6. Staff safety/support and clearly document response expectations. The current SOS dial/share tools are user-operated; report storage is not an emergency dispatch system. Do not market 24/7 monitoring, police notification or guaranteed safety as implemented.
7. Test on physical Android/iPhone devices: permission denial, dialler/share sheets, network loss, app backgrounding, Cashfree return, concurrent bookings and session expiry. Create signed builds and complete store review using owner accounts.
8. Establish auditable accounting for the 50%-of-annual-net-profit-after-tax pledge, planting partners, irrigation and survival reporting. No environmental results are claimed without supporting records.
