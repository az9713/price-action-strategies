# Follow-up acceptance investigation: global saved-result ownership

Code-inspection finding, not an executed failure or final acceptance result.

`frontend/src/App.tsx::openResult` currently updates activeJob/result before awaiting the individual saved report, and has no request-generation guard for overlapping global loads. The navigation revision only prevents a late page redirect. A delayed previous request may therefore leave another account's report with the new active job ID, or overwrite a later selection. Current browser coverage deliberately delays an inline sensitivity account response while leaving Validation; it does not prove the overlapping global load case.

Next: first exercise two genuinely saved accounts with deliberately reversed global result/report response order. Check report identity, displayed values, export job/part URL and the user's selected page throughout. Then bind global loading/commit to the latest requested account, clear or retain complete previous identity atomically, and test both stale success and stale failure. Keep ordinary experiment/search/final/portfolio and aggregate redirection coverage. Do not promote the existing eight journeys to all global ownership acceptance.

## Executed follow-up

The risk was reproduced with real saved accounts in receipt20261108T174226243825Z. The loader fix passes the identical reproduction in20261108T174456934938Z. Both desktop profiles now test reversed success, stale failure and current failure, and the complete ten-journey suite passes in20261108T174501602436Z. This closes that scoped finding; it does not certify every global navigation/final/portfolio combination.
