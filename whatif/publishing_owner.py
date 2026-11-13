"""Browser-only confirmation for the TikTok Studio operator."""
from datetime import datetime, timezone
from html import escape
from urllib.parse import urlencode

from scripts import publishing_accounts as accounts
from scripts.publishing_direct import require
from . import hosted_tiktok, youtube


def studio_binding(drafts, alias):
    row = accounts.registry(drafts.root).get(alias)
    require(row and row['platform'] == 'tiktok' and row.get('handle'), 'Register the intended TikTok handle')
    return {**row, 'account': alias}


def studio_link(origin, alias, draft=None):
    return origin.rstrip('/') + '/owner/studio?' + urlencode({'account': alias, **({'draft': draft} if draft else {})})


def pending(drafts, draft_id, alias):
    draft = drafts.get(draft_id)
    row = next((r for r in draft['destinations'] if r['account'] == alias and r['platform'] == 'tiktok'), None)
    state = next((r for r in draft['deliveries'] if r['alias'] == alias), None)
    require(row and state and state['status'] == 'action_required' and state['receipt'].get('handed_off_at'),
            'A pending TikTok Studio handoff is required')
    binding = studio_binding(drafts, alias)
    require(all(row[key] == binding[key] for key in ('account_id', 'handle')), 'The reviewed account changed')
    return row, state


def handle_form(drafts, form):
    alias = form['account']
    row = studio_binding(drafts, alias)
    if not form.get('draft'):
        proof = hosted_tiktok.confirm_studio_account(row['handle'], form['observed_handle'], 'owner')
        folder = drafts.directory / 'grants'
        folder.mkdir(mode=0o700, exist_ok=True)
        youtube.atomic_json(folder / (alias + '.studio.json'), {**proof, 'account_id': row['account_id']})
        return 'Studio account confirmed. Return to ChatGPT and verify the account.'
    row, state = pending(drafts, form['draft'], alias)
    observation = hosted_tiktok.BrowserObservation(
        'owner', form['url'], form['observed_handle'], form.get('observed_caption', ''),
        datetime.now(timezone.utc), form.get('matches') == 'yes', form.get('public') == 'yes')
    receipt = hosted_tiktok.verify_publication(row, form['url'], handed_off_at=state['receipt']['handed_off_at'],
                                               browser_observation=observation)
    require(receipt['status'] == 'published', 'Check the post against the reviewed media, account and caption')
    drafts.confirm_tiktok(form['draft'], alias, receipt)
    return 'Publication recorded from your browser verification. Retrieve the draft in ChatGPT for its receipt.'


def page(drafts, alias, draft_id):
    row = studio_binding(drafts, alias)
    html = ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Ifverse TikTok Studio</title>'
            '<h1>Ifverse TikTok Studio</h1><p>Expected account <strong>' + escape(row['handle']) + '</strong></p>'
            '<form method="post" action="/owner/studio"><input type="hidden" name="account" value="'
            + escape(alias, quote=True) + '">')
    if not draft_id:
        return html + ('<p>Open <a href="https://www.tiktok.com/tiktokstudio/upload" rel="noreferrer">TikTok Studio</a>'
                       ' and check the active handle.</p><label>Handle shown in Studio '
                       '<input name="observed_handle" required></label> <button>Confirm account</button></form>')
    row, _ = pending(drafts, draft_id, alias)
    url = escape(drafts.adapter.media_url(row['media_sha256']), quote=True)
    return html + ('<input type="hidden" name="draft" value="' + escape(draft_id, quote=True) + '">'
                   '<p>Open the resulting public post in Chrome and compare it with the reviewed export.</p>'
                   '<p><a href="' + url + '">Open reviewed video</a></p>'
                   '<p>Reviewed caption</p><pre>' + escape(row['caption']) + '</pre>'
                   '<p><label>Public post URL <input type="url" name="url" required></label></p>'
                   '<p><label>Handle on the post <input name="observed_handle" required></label></p>'
                   '<p><label>Caption on the post <textarea name="observed_caption"></textarea></label></p>'
                   '<p><label><input type="checkbox" name="matches" value="yes" required> '
                   'I compared the published video with the reviewed export.</label></p>'
                   '<p><label><input type="checkbox" name="public" value="yes" required> '
                   'I verified the post opens publicly.</label></p><button>Record verification</button></form>')
