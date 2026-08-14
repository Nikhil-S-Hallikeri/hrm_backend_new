from django.apps import AppConfig
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

# Shared by both the scheduled-campaigns worker and the reminder/follow-up automation engine.
# Was 20 - on this box's actual capacity (1 vCPU, ~3.8GB RAM, shared with several other tenants'
# services and a max_connections=100 Postgres), 20 concurrent tasks each opening their own DB
# connection and making outbound WhatsApp/Meta API calls was enough concurrent load, during a
# multi-hundred-contact bulk reminder run, to push the box into repeated OOM kills (see the
# 2026-08-08 incident: Postgres itself got OOM-killed multiple times mid-campaign). Lower
# concurrency trades send throughput for stability - deliberately favoring "slow but reliable"
# over "fast but crashes the shared database" given this box's real resource ceiling.
executor = ThreadPoolExecutor(max_workers=3)

def _process_scheduled_campaign_task(campaign_id):
    from django.db import connection
    from django.utils import timezone
    from whatsapp_app.models import Campaign
    from whatsapp_app.utils import execute_campaign
    import logging
    logger = logging.getLogger(__name__)
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        logger.info(f"Thread pool executing scheduled campaign: {campaign.name} (ID: {campaign.id})")
        execute_campaign(campaign)
    except Exception as campaign_err:
        logger.error(f"Error executing scheduled campaign {campaign_id}: {str(campaign_err)}")
        try:
            campaign = Campaign.objects.get(id=campaign_id)
            campaign.status = 'FAILED'
            campaign.completed_at = timezone.now()
            campaign.save(update_fields=['status', 'completed_at'])
        except Exception:
            pass
    finally:
        connection.close()

def _process_follow_up_task(contact_id, workflow_id, step_to_send_id, next_step_id, state_id):
    from django.db import connection
    from django.utils import timezone
    from datetime import timedelta
    from whatsapp_app.models import Contact, FollowUpWorkflow, FollowUpStep, FollowUpContactState, AutomationLog
    from whatsapp_app.utils import send_automation_message
    import logging
    logger = logging.getLogger(__name__)

    try:
        contact = Contact.objects.get(id=contact_id)
        workflow = FollowUpWorkflow.objects.get(id=workflow_id)
        step_to_send = FollowUpStep.objects.get(id=step_to_send_id)
        next_step = FollowUpStep.objects.get(id=next_step_id) if next_step_id else None
        state = FollowUpContactState.objects.get(id=state_id)

        try:
            logger.info(f"Automation Engine: Sending follow-up '{workflow.name}' step {step_to_send.step_number} to {contact.phone_number}")
            send_automation_message(contact, step_to_send.template, step_to_send.media_url, getattr(step_to_send, 'template_variables', None))
            
            state.current_step = step_to_send
            state.retry_count = 0
            
            if next_step:
                state.status = 'SENT'
                state.next_execution_time = timezone.now() + timedelta(seconds=next_step.delay_seconds)
            else:
                state.status = 'COMPLETED'
                state.next_execution_time = timezone.now()

            state.save()

            AutomationLog.objects.create(
                whatsapp_config=workflow.whatsapp_config,
                automation_type='FOLLOW_UP',
                contact=contact,
                action_type='SENT',
                details=f"Successfully sent Follow-up '{workflow.name}' Step {step_to_send.step_number} template: {step_to_send.template.name}"
            )
        except Exception as send_err:
            logger.error(f"Failed to send follow-up step: {send_err}")
            state.retry_count += 1
            if state.retry_count >= 3:
                state.status = 'FAILED'
            state.save()

            AutomationLog.objects.create(
                whatsapp_config=workflow.whatsapp_config,
                automation_type='FOLLOW_UP',
                contact=contact,
                action_type='FAILED',
                details=f"Failed to send Follow-up '{workflow.name}' Step {step_to_send.step_number}. Error: {str(send_err)} (Retry: {state.retry_count})"
            )
    except Exception as e:
        logger.error(f"Follow up task error: {e}")
    finally:
        from django.db import close_old_connections
        close_old_connections()

def _process_reminder_task(contact_id, campaign_id, schedule_id, exec_state_id):
    from django.db import close_old_connections
    from django.utils import timezone
    from whatsapp_app.models import Contact, ReminderCampaign, ReminderSchedule, ReminderExecution, AutomationLog
    from whatsapp_app.utils import send_automation_message
    import logging
    logger = logging.getLogger(__name__)

    close_old_connections()
    message_sent = False
    try:
        contact = Contact.objects.get(id=contact_id)
        campaign = ReminderCampaign.objects.get(id=campaign_id)
        schedule = ReminderSchedule.objects.get(id=schedule_id)
        exec_state = ReminderExecution.objects.get(id=exec_state_id)

        try:
            logger.info(f"Automation Engine: Sending reminder '{campaign.name}' ({schedule.timing_type}) to {contact.phone_number}")
            send_automation_message(contact, schedule.template, schedule.media_url, getattr(schedule, 'template_variables', None))
            message_sent = True
        except Exception as send_err:
            logger.error(f"Failed to send reminder campaign: {send_err}")
            exec_state.retry_count += 1
            exec_state.status = 'FAILED' if exec_state.retry_count >= 3 else 'PENDING'
            exec_state.save()

            AutomationLog.objects.create(
                whatsapp_config=campaign.whatsapp_config,
                automation_type='REMINDER',
                contact=contact,
                action_type='FAILED',
                details=f"Failed to send Reminder Campaign '{campaign.name}' schedule {schedule.timing_type}. Error: {str(send_err)} (Retry: {exec_state.retry_count})"
            )
            return

        # The real WhatsApp message has already gone out at this point - nothing below may
        # ever cause this execution to fall back to PENDING/IN_PROGRESS and get resent, even
        # if the DB write here has a hiccup. (This is exactly what caused duplicate sends
        # during today's incident: a bookkeeping failure after a successful send was being
        # treated identically to a send failure, so the "failed" row got retried and the
        # already-delivered message went out again.) Bookkeeping errors are logged loudly
        # instead of raised, so the outer except below - whose job is to unstick rows that
        # never got attempted at all - never sees them and never re-queues this one.
        try:
            exec_state.status = 'SENT'
            exec_state.sent_at = timezone.now()
            exec_state.save()
        except Exception as save_err:
            logger.error(f"Reminder task error: sent reminder to {contact.phone_number} but failed to save SENT status for execution {exec_state_id}: {save_err}")

        try:
            AutomationLog.objects.create(
                whatsapp_config=campaign.whatsapp_config,
                automation_type='REMINDER',
                contact=contact,
                action_type='SENT',
                details=f"Successfully sent Reminder Campaign '{campaign.name}' schedule {schedule.timing_type} template: {schedule.template.name}"
            )
        except Exception as log_err:
            logger.error(f"Reminder task error: sent reminder to {contact.phone_number} but failed to write AutomationLog for execution {exec_state_id}: {log_err}")

    except Exception as e:
        logger.error(f"Reminder task error: {e}")
        if message_sent:
            # The send itself already succeeded - whatever failed was bookkeeping around it.
            # Never let this fall through to the resend-eligible reset below.
            pass
        else:
            # Nothing was sent. Whatever failed above (contact/campaign/schedule/exec_state
            # lookup, a DB hiccup, etc.), the main loop already flipped this row to IN_PROGRESS
            # before submitting it here. If we don't undo that, the row is permanently invisible
            # to both the "already sent" and "still pending" checks - it never gets a SENT or
            # FAILED status and never gets retried. Always try to unstick it via its id, since
            # exec_state itself may not have been fetched yet when this triggered.
            try:
                from whatsapp_app.models import ReminderExecution
                stuck = ReminderExecution.objects.get(id=exec_state_id)
                if stuck.status == 'IN_PROGRESS':
                    stuck.retry_count += 1
                    stuck.status = 'FAILED' if stuck.retry_count >= 3 else 'PENDING'
                    stuck.save(update_fields=['status', 'retry_count'])
            except Exception as reset_err:
                logger.error(f"Reminder task error: failed to reset stuck execution {exec_state_id}: {reset_err}")
    finally:
        close_old_connections()


def start_scheduled_campaigns_worker():
    time.sleep(3)
    from django.utils import timezone
    from django.db import close_old_connections
    from whatsapp_app.models import Campaign
    import logging
    logger = logging.getLogger(__name__)

    logger.info("Auto-started background scheduled campaigns worker thread.")
    while True:
        try:
            close_old_connections()
            now = timezone.now()
            scheduled_campaigns = Campaign.objects.filter(
                status='SCHEDULED',
                scheduled_at__lte=now
            )
            for campaign in scheduled_campaigns:
                campaign.status = 'IN_PROGRESS'
                campaign.save(update_fields=['status'])
                executor.submit(_process_scheduled_campaign_task, campaign.id)
        except Exception as e:
            logger.error(f"Background campaigns worker loop error: {e}")
        finally:
            close_old_connections()
            time.sleep(10)

def start_automation_engine_worker():
    time.sleep(5)
    from django.utils import timezone
    from django.db import close_old_connections
    from django.db.models import F, Q
    from datetime import timedelta
    from whatsapp_app.models import (
        Contact, FollowUpWorkflow, FollowUpContactState,
        ReminderCampaign, ReminderSchedule, ReminderExecution
    )
    import logging
    logger = logging.getLogger(__name__)

    # Import timezone library â€” prefer pytz, fall back to zoneinfo (Python 3.9+)
    try:
        import pytz as _tz_lib
        def _localize(dt, tz_name):
            return _tz_lib.timezone(tz_name).localize(dt)
    except ImportError:
        from zoneinfo import ZoneInfo
        def _localize(dt, tz_name):
            return dt.replace(tzinfo=ZoneInfo(tz_name))

    logger.info("Auto-started background follow-up & reminder automation engine worker thread.")
    while True:
        try:
            close_old_connections()
            now = timezone.now()

            # A. FOLLOW-UPS
            active_workflows = FollowUpWorkflow.objects.filter(is_active=True)
            # A. FOLLOW-UPS (Wrapped safely so followups errors never block reminders)
            try:
                for workflow in active_workflows:
                    steps = list(workflow.steps.all().order_by('step_number'))
                    if not steps: continue
                    eligible_contacts = Contact.objects.filter(
                        whatsapp_config=workflow.whatsapp_config,
                        last_message_time__isnull=False
                    ).filter(
                        Q(last_customer_message_time__isnull=True) | 
                        Q(last_message_time__gt=F('last_customer_message_time'))
                    )

                    for contact in eligible_contacts:
                        state = FollowUpContactState.objects.filter(contact=contact, workflow=workflow).first()
                        created = False
                        if not state:
                            state = FollowUpContactState.objects.create(
                                contact=contact, workflow=workflow, status='PENDING', next_execution_time=now
                            )
                            created = True
                        if not created and state.status in ['COMPLETED', 'CANCELLED', 'FAILED']:
                            if contact.last_message_time > state.updated_at:
                                state.status = 'PENDING'
                                state.current_step = None
                                state.retry_count = 0
                                state.next_execution_time = contact.last_message_time
                                state.save()
                        if state.status not in ['PENDING', 'SENT'] or state.retry_count >= 3:
                            continue

                        step_to_send = None
                        next_step = None
                        if state.current_step is None:
                            step_to_send = steps[0]
                            if len(steps) > 1: next_step = steps[1]
                        else:
                            try:
                                curr_idx = steps.index(state.current_step)
                                if curr_idx + 1 < len(steps):
                                    step_to_send = steps[curr_idx + 1]
                                    if curr_idx + 2 < len(steps): next_step = steps[curr_idx + 2]
                            except ValueError:
                                continue
                        if not step_to_send: continue

                        trigger_time = contact.last_message_time + timedelta(seconds=step_to_send.delay_seconds)
                        if now >= trigger_time:
                            state.status = 'IN_PROGRESS'
                            state.save(update_fields=['status'])
                            executor.submit(
                                _process_follow_up_task,
                                contact.id, workflow.id, step_to_send.id,
                                next_step.id if next_step else None,
                                state.id
                            )

            except Exception as fu_err:
                logger.error(f"Follow-ups loop error: {fu_err}")

            # B. REMINDERS

            # Self-heal: a genuinely in-flight send completes in seconds, but a row is marked
            # IN_PROGRESS the moment it's submitted to `executor`, not when a worker actually
            # picks it up - with only max_workers=3 (throttled down from 20, see executor
            # above) and a several-hundred-contact backlog, a queued-but-not-yet-started task
            # can easily sit IN_PROGRESS for well past 3 minutes without anything being wrong.
            # A too-short cutoff here previously caused this same reclaim loop to treat normal
            # queue wait as a hang, burn through retry_count, and mark hundreds of never-
            # attempted contacts FAILED mid-backlog. 20 minutes comfortably covers a full
            # backlog drain at max_workers=3 while still catching genuinely hung workers
            # (DB stall, process restart mid-send, etc.) that died without ever reaching
            # either except block in _process_reminder_task and can't reset themselves.
            try:
                stale_cutoff = now - timedelta(minutes=20)
                for stale in ReminderExecution.objects.filter(status='IN_PROGRESS', updated_at__lt=stale_cutoff):
                    stale.retry_count += 1
                    stale.status = 'FAILED' if stale.retry_count >= 3 else 'PENDING'
                    stale.save(update_fields=['status', 'retry_count'])
            except Exception as heal_err:
                logger.error(f"Stale reminder execution reclaim error: {heal_err}")

            active_campaigns = ReminderCampaign.objects.filter(is_active=True)
            try:
                with open('webhook_debug.log', 'a') as _dbg:
                    _dbg.write(f"\n[REMINDER LOOP TICK] {now.strftime('%H:%M:%S')} UTC | active_campaigns={active_campaigns.count()}\n")
            except Exception:
                pass
            for campaign in active_campaigns:
                schedules = ReminderSchedule.objects.filter(reminder_campaign=campaign)
                for schedule in schedules:
                    mins_map = {
                        '7_DAYS_BEFORE': 7 * 24 * 60,
                        '5_DAYS_BEFORE': 5 * 24 * 60,
                        '3_DAYS_BEFORE': 3 * 24 * 60,
                        '2_DAYS_BEFORE': 2 * 24 * 60,
                        '1_DAY_BEFORE': 1 * 24 * 60,
                        '6_HOURS_BEFORE': 6 * 60,
                        '1_HOUR_BEFORE': 60,
                        'AT_EVENT_TIME': 0,
                    }
                    if schedule.timing_type == 'SPECIFIC_DATETIME' and schedule.template_variables and schedule.template_variables.get('scheduled_datetime'):
                        try:
                            from django.utils.dateparse import parse_datetime
                            raw_dt_str = str(schedule.template_variables.get('scheduled_datetime')).strip()
                            parsed = parse_datetime(raw_dt_str)
                            if parsed:
                                if timezone.is_naive(parsed):
                                    tz_name = campaign.time_zone if (campaign.time_zone and campaign.time_zone != 'UTC') else 'Asia/Kolkata'
                                    execution_time = _localize(parsed, tz_name)
                                else:
                                    execution_time = parsed
                            else:
                                execution_time = campaign.event_date_time
                        except Exception as _parse_err:
                            execution_time = campaign.event_date_time
                            try:
                                with open('webhook_debug.log', 'a') as _dbg:
                                    _dbg.write(f"  [SCHED {schedule.id}] PARSE ERROR: {_parse_err}\n")
                            except Exception:
                                pass
                    else:
                        minutes = mins_map.get(schedule.timing_type, schedule.custom_minutes_before or 0)
                        execution_time = campaign.event_date_time - timedelta(minutes=minutes)

                    try:
                        with open('webhook_debug.log', 'a') as _dbg:
                            _dbg.write(f"  [SCHED {schedule.id}] type={schedule.timing_type} exec_time={execution_time} now>={now>=execution_time}\n")
                    except Exception:
                        pass

                    if now >= execution_time:
                        contacts = campaign.contacts.all()
                        if not contacts.exists():
                            contacts = Contact.objects.filter(whatsapp_config=campaign.whatsapp_config)
                        for contact in contacts:
                            try:
                                exec_state, created = ReminderExecution.objects.get_or_create(
                                    reminder_campaign=campaign, contact=contact, schedule=schedule,
                                    defaults={'status': 'PENDING', 'execution_time': execution_time, 'context_data': {}, 'state': 'PENDING'}
                                )
                            except ReminderExecution.MultipleObjectsReturned:
                                executions = list(ReminderExecution.objects.filter(
                                    reminder_campaign=campaign, contact=contact, schedule=schedule
                                ).order_by('id'))
                                exec_state = executions[0]
                                created = False
                                for dup in executions[1:]:
                                    dup.delete()
                            if exec_state.status != 'PENDING' or exec_state.retry_count >= 3:
                                continue
                            
                            exec_state.status = 'IN_PROGRESS'
                            exec_state.save(update_fields=['status'])
                            executor.submit(
                                _process_reminder_task,
                                contact.id, campaign.id, schedule.id, exec_state.id
                            )

        except Exception as e:
            logger.error(f"Automation engine loop error: {e}")
            try:
                import traceback
                with open('webhook_debug.log', 'a') as _dbg:
                    _dbg.write(f"\n[AUTOMATION LOOP ERROR] {e}\n{traceback.format_exc()}\n")
            except Exception:
                pass
        finally:
            close_old_connections()
            time.sleep(10)

class WhatsappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'  # type: ignore
    name = 'whatsapp_app'
    _threads_started = False

    def ready(self):
        import whatsapp_app.signals
        import sys
        is_manage_cmd = any(cmd in sys.argv for cmd in ['migrate', 'makemigrations', 'collectstatic', 'shell', 'test'])
        is_runserver = 'runserver' in sys.argv
        if not is_manage_cmd and not WhatsappConfig._threads_started:
            # If running via runserver, only start threads in the active child process (RUN_MAIN == 'true')
            # to prevent duplicate background tasks executing in both the reloader parent and child.
            if (is_runserver and os.environ.get('RUN_MAIN') == 'true') or (not is_runserver):
                WhatsappConfig._threads_started = True
                threading.Thread(target=start_scheduled_campaigns_worker, daemon=True).start()
                threading.Thread(target=start_automation_engine_worker, daemon=True).start()

