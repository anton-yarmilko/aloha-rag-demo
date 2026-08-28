# POS Troubleshooting (synthetic demo data)

All entries below are invented for demo purposes and contain no proprietary information.

## Kitchen printer offline
Check the printer power and the interface cable first. Ping the printer IP from the
BOH server. If it responds, restart the print spooler service on the terminal that
owns the queue. If it does not respond, power-cycle the printer and re-check the
static IP configuration against the site network sheet.

## Terminal stuck in boot loop
Boot the terminal into safe mode and check free disk space. Clear the local temp
folder if usage is above 95 percent. If the loop continues, rename the local spool
directory and let the application rebuild it on next start.

## Credit card batch did not settle
Open the EDC utility and check the batch status. If the batch shows open, verify
the processor gateway is reachable from the BOH server. Re-run settlement manually
and confirm the response code. Never delete a batch - escalate if settlement fails twice.

## Manager cannot apply a discount
Verify the employee job code has the discount permission enabled. If permissions
look correct, check whether the discount item is active for the current day part.

## Orders not reaching the kitchen display
Confirm the KDS controller service is running. Check the routing rules for the
revenue center - a misconfigured routing rule silently drops items.
