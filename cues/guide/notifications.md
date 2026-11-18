# Notifications

ReelTime can tell your phone when someone uses a review link: a comment
or a reply, or a link being opened. The notification's title is the
project's name, and tapping it opens the cue's page at that version.

## On an iPhone or iPad

Notifications need ReelTime on the Home Screen (iOS 16.4 or later):

1. Open ReelTime in Safari and sign in.
2. Tap Share, then **Add to Home Screen**.
3. Open ReelTime from the Home Screen and sign in there too: it keeps
   its own sign-in, apart from Safari's.
4. In the profile menu, **Notifications**, then **Turn On for This
   Device**, and allow notifications when iOS asks.

## On a Computer or an Android Phone

Open **Notifications** in the profile menu and **Turn On for This
Device**. Chrome, Edge, Firefox and Safari can all show them.

## What You're Told About

- **Comments and Replies**: "Jane (guest) commented on 1m05 v2", with
  the start of what they wrote. Your own comments don't notify you.
- **Review Links Opened**: "Jane (guest) opened 1m05 v2", when a guest or
  a viewer starts watching. A reload within half an hour is the same
  visit, and a link opened again soon after doesn't notify you twice.

Untick either under **Tell Me About**. A guest's name always says
"(guest)": they can type any name, so only names without it are sure
to be who they say.

Several comments on one cue close together arrive as one notification:
"3 new comments on 1m05 v2".

## Devices

The page lists every device you turned on. **Send Test** sends a
notification to one; **Remove** stops it. Signing out of ReelTime turns
the device you're on off too.

Notifications stop on their own when you lose your ReelTime role. After
a restore from a backup, turn them on again on each device.

Whoever runs ReelTime: notifications are sent by the scheduler service
(or `reeltime-push.service` without Docker), which needs to reach Apple's,
Google's, Mozilla's and Microsoft's push services over the internet.
