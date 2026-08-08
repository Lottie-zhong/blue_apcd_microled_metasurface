# Legacy case-hash compatibility

`TEST40_CASE_UID_V1` is the sole formal Test40 case identity. The DOE96 canonical case-hash builder was not recovered; DOE96 hashes are not inherited or synthesized. Any legacy `case_hash` column is retained only as `null` with status `NOT_APPLICABLE_TEST40_USES_TEST_CASE_UID_V1`.
