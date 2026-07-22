# Auth-Gated App Testing Playbook (Emergent Google OAuth)

## Step 1: Create Test User & Session (via mongosh)
```
mongosh --eval "
use('test_database');
var userId = 'test-user-' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({
  user_id: userId,
  email: 'test.user.' + Date.now() + '@example.com',
  name: 'Test User',
  picture: 'https://via.placeholder.com/150',
  auth_provider: 'google',
  created_at: new Date()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
print('Session token: ' + sessionToken);
print('User ID: ' + userId);
"
```

## Step 2: Test Backend API
```
curl -X GET "$REACT_APP_BACKEND_URL/api/auth/me" \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

## Step 3: Browser Test
Set cookie `session_token` on the app domain with httpOnly, secure, sameSite=None, then navigate to `/dashboard`.

## Checklist
- [ ] users doc has `user_id` (custom UUID) field.
- [ ] session doc has matching `user_id`.
- [ ] All queries use `{"_id": 0}` projection.
- [ ] `/api/auth/me` returns user data with session_token cookie OR Bearer header.
