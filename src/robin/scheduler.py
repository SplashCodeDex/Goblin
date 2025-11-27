import time
import schedule
from datetime import datetime
from croniter import croniter
from robin.database import get_active_queries, update_last_run_timestamp, save_run, create_notification
from robin.llm import get_llm, refine_query, filter_results, generate_summary_and_artifacts
from robin.search import get_search_results
from robin.scrape import scrape_multiple
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_investigation(query_details: dict):
    """
    Runs a full investigation for a single scheduled query.
    This function orchestrates the entire OSINT pipeline.
    """
    query_text = query_details['query_text']
    query_id = query_details['id']
    query_name = query_details['name']

    logging.info(f"Running scheduled query #{query_id}: '{query_text}'")

    try:
        # For now, we use the default model. This could be a parameter in the future.
        model = os.getenv("DEFAULT_MODEL", "gpt4o")
        llm = get_llm(model)

        # 1. Refine Query
        refined = refine_query(llm, query_text)
        logging.info(f"Refined query: {refined}")

        # 2. Search
        # Note: These parameters should be configurable in a real implementation
        results = get_search_results(refined.replace(" ", "+"), max_workers=4, max_results=50, request_timeout=30)
        logging.info(f"Found {len(results)} search results.")

        # 3. Filter
        filtered = filter_results(llm, refined, results)
        logging.info(f"Filtered down to {len(filtered)} results.")

        # 4. Scrape
        scraped_content, _ = scrape_multiple(filtered, max_workers=4, request_timeout=30)
        logging.info(f"Scraped {len(scraped_content)} pages.")

        # 5. Summarize and Extract Artifacts
        report = generate_summary_and_artifacts(llm, query_text, scraped_content)
        logging.info("Generated summary and artifacts.")

        # 6. Save the run to the main history table
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "query": f"[Scheduled] {query_text}",
            "refined": refined,
            "results": results,
            "filtered": filtered,
            "scraped": scraped_content,
            "summary": report.get("summary", ""),
        }
        run_id = save_run(entry)
        logging.info(f"Saved investigation as run #{run_id}.")

        # 7. Update the last run timestamp for the scheduled query
        update_last_run_timestamp(query_id, datetime.utcnow().isoformat() + "Z")
        logging.info(f"Updated last run time for scheduled query #{query_id}.")

        # 8. Create a notification
        notification_message = f"Scheduled query '{query_name}' completed successfully. Run ID: {run_id}"
        create_notification(query_id, run_id, notification_message)
        logging.info(f"Created notification for scheduled query #{query_id}.")

    except Exception as e:
        logging.error(f"Failed to run investigation for query #{query_id}: {e}", exc_info=True)


def check_and_run_due_queries():
    """
    Checks for scheduled queries that are due and runs them.
    Uses croniter to parse the schedule and compare with the last run time.
    """
    logging.info("Scheduler checking for due queries...")
    active_queries = get_active_queries()

    if not active_queries:
        logging.info("No active queries found.")
        return

    now = datetime.utcnow()

    for query in active_queries:
        schedule_str = query['schedule']
        last_run_str = query.get('last_run_timestamp')

        if not croniter.is_valid(schedule_str):
            logging.error(f"Invalid cron schedule for query #{query['id']}: {schedule_str}")
            continue

        # If never run, assume it's due if the schedule allows (or just run it once)
        # For simplicity, if never run, we treat it as due immediately or check if a run was missed.
        # Let's say if never run, we run it.
        if not last_run_str:
            logging.info(f"Query #{query['id']} has never run. Running now.")
            run_investigation(query)
            continue

        last_run = datetime.fromisoformat(last_run_str.replace("Z", ""))

        # Calculate the next expected run time AFTER the last run
        iter = croniter(schedule_str, last_run)
        next_run = iter.get_next(datetime)

        if next_run <= now:
            logging.info(f"Query #{query['id']} is due (next run was {next_run}). Running now.")
            run_investigation(query)
        else:
            logging.debug(f"Query #{query['id']} is not due yet. Next run: {next_run}")


if __name__ == "__main__":
    logging.info("Starting the Robin scheduler...")

    # Run once on startup
    check_and_run_due_queries()

    # Schedule the job to run every hour.
    # In a real-world scenario, the scheduler would be more dynamic,
    # checking every minute and using croniter to see if any jobs are due.
    schedule.every().hour.do(check_and_run_due_queries)

    logging.info("Scheduler started. Will run checks every hour.")

    while True:
        schedule.run_pending()
        time.sleep(1)
