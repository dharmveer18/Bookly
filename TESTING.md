# Testing plan

Tests live in `bookings/tests/` (one file per concern). Run with:

```
python manage.py test bookings
```

CI (`.github/workflows/django.yml`) does not run the suite yet - the
`# Run tests` step is still commented out. That's Phase 5 below.

## Done

- **Phase 1 - `test_admin.py`** (8 tests): appointment admin flows - price
  auto-fill for single/multi-service bookings, the confirmation-timing
  fix, the dashboard redirect, the `/edit/` URL, client details page's
  upcoming/completed lists. Caught a real bug: editing an existing
  service line's service never refreshed its price (fixed in
  `AppointmentAdmin.save_formset`).
- **Phase 2 - `test_commands.py`** (9 tests): `send_appointment_reminders`
  (24h window, skips already-reminded/cancelled/out-of-window/past,
  double-run doesn't double-send) and `ensure_superuser` (creates once,
  skips if one exists, skips if env vars missing).

Staff is deliberately excluded from test scope (only fixture data where
required) - see the "Hide Staff selection from the appointment form"
commit.

## Remaining

### Phase 3 - `test_models.py` (pure logic, no DB round-trips needed beyond fixtures)
- `Appointment.end_time` sums service durations correctly, including
  zero services
- `Appointment.__str__` 12-hour time formatting
- `AppointmentService.save()` auto-fills price only when not already set
- `to_e164()` in `bookings/whatsapp.py`: local number -> E.164,
  already-E.164 passes through, messy input (spaces/dashes)

### Phase 4 - `test_urls.py` (routing sanity)
- `/healthz/` returns 200 without auth - direct regression test for the
  admin catch-all bug found this session
- `/` requires login
- old `/admin/` prefix 404s (confirms the move to root took effect)

### Phase 5 - wire into CI
- Uncomment the `# python manage.py test` step in
  `.github/workflows/django.yml`
- Open question from the original discussion, still unresolved: should
  CI test against SQLite (current, fast, matches nothing in prod) or
  Postgres (matches prod/Neon, slower, needs a service container in the
  workflow)?
