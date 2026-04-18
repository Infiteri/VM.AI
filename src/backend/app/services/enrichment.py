import dateparser
from datetime import datetime
from typing import Optional, Any, Tuple
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.draft import TaskDraft
from app.models.statistics import (
    TaskStatistics,
    CategoryStatistics,
    TaskStatisticsLocation,
    CategoryStatisticsLocation,
)
from app.services.task_matcher import task_matcher
from app.core.logging_config import setup_logging

logger = setup_logging()


class EnrichmentService:
    """
    Task enrichment service with two-phase execution.

    Phase 1 (Predict):  Overwrite -> DateParse -> DraftSave
    Phase 2 (Commit):   DraftLoad/DraftMerge/ChangeMerge -> Compute

    Public Methods:
        predict_nlp_add()   - NLP add flow (Phase 1 only)
        commit_from_draft()  - Draft commit flow (Phase 2 only)
        commit_manual()      - Manual creation (Phase 1 + 2)
        merge_nlp_modify()   - NLP modify flow
        update_task()        - Update task with computed fields
    """

    # ================================================================
    # MAIN PUBLIC METHODS
    # ================================================================

    def predict_nlp_add(
        self,
        db: Session,
        nlp_payload: dict[str, dict[str, Any]],
        match_result: dict[str, Any],
    ) -> Tuple[dict[str, Any], UUID]:
        """
        NLP add flow (Phase 1 only).

        Input:
            nlp_payload: Task fields with {value, predicted} structure
            match_result: Result from task_matcher.find_match()

        Returns:
            (clean_task_payload, draft_id)
            - clean_task_payload: TaskPayload with resolved dates, overwritten fields
            - draft_id: UUID of saved draft

        Steps:
            1. Parse date strings to datetime (first, for importance calculation)
            2. Determine overwrite map based on match status + datetime deadline
            3. Overwrite predicted fields with historical data
            4. Save to draft table
        """
        logger.info(f"Enrichment: predict_nlp_add started")
        logger.debug(f"  Input NLP payload keys: {list(nlp_payload.keys())}")
        logger.debug(f"  Match status: {match_result.get('association_status')}")

        # First parse dates (flat structure needed for _get_overwrite_map)
        flat_payload = {}
        for field, entry in nlp_payload.items():
            value, _ = self._extract_field(entry)
            flat_payload[field] = value

        parsed_task = self._date_parse(flat_payload)

        # Rebuild nlp_payload with parsed datetime for importance calculation
        nlp_payload_with_dates = nlp_payload.copy()
        for field in ["start", "deadline", "fixed_start"]:
            if field in parsed_task and parsed_task[field] is not None:
                nlp_payload_with_dates[field] = {
                    "value": parsed_task[field],
                    "predicted": nlp_payload.get(field, {}).get("predicted", False),
                }

        overwrite_map = self._get_overwrite_map(
            db, match_result, nlp_payload_with_dates
        )

        enriched_task = self._overwrite_fields(parsed_task, overwrite_map)

        draft_id = self._draft_save(db, enriched_task, match_result)

        logger.info(f"Enrichment: predict_nlp_add complete. Draft ID: {draft_id}")
        logger.debug(f"  Output task keys: {list(parsed_task.keys())}")
        return parsed_task, draft_id

    def commit_from_draft(
        self,
        db: Session,
        request_task: dict[str, Any],
        draft_id: UUID,
    ) -> dict[str, Any]:
        """
        Draft commit flow (Phase 2 only).

        Input:
            request_task: Task data from frontend request (source of truth)
            draft_id: UUID of saved draft

        Returns:
            full_task_data: Complete task data with internal refs, ready for DB

        Steps:
            1. Load draft (including match_result) from DB
            2. Merge request with draft (request priority)
            3. Compute urgency/value
            4. Add internal refs (loaded from draft)
        """
        logger.info(f"Enrichment: commit_from_draft started for draft '{draft_id}'")

        draft_data = self._draft_load(db, draft_id)
        if not draft_data:
            logger.warning(f"Draft {draft_id} not found, using request only")
            draft_data = {}

        match_result = draft_data.get("match_result", {})

        merged_task = self._draft_merge(request_task, draft_data)

        full_task_data = self._compute(merged_task)

        full_task_data = self._add_internal_refs(full_task_data, match_result)

        logger.info(
            f"Enrichment: commit_from_draft complete. "
            f"Value: {full_task_data.get('value')}, "
            f"Status: {match_result.get('association_status')}"
        )
        logger.debug(f"  full_task_data keys: {list(full_task_data.keys())}")
        return full_task_data

    def commit_manual(
        self,
        db: Session,
        task_payload: dict[str, Any],
        match_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Manual creation flow (Phase 1 + 2 combined).

        Input:
            task_payload: User-filled task data (TaskPayload, all explicit)
            match_result: Result from task_matcher.find_match()

        Returns:
            full_task_data: Complete task data with internal refs, ready for DB

        Steps:
            1. Compute urgency/value (no overwrite - all fields explicit)
            2. Add internal refs
        """
        logger.info(
            f"Enrichment: commit_manual started for '{task_payload.get('name')}'"
        )

        full_task_data = self._compute(task_payload)

        full_task_data = self._add_internal_refs(full_task_data, match_result)

        logger.info(
            f"Enrichment: commit_manual complete. "
            f"Value: {full_task_data.get('value')}, "
            f"Status: {match_result.get('association_status')}"
        )
        return full_task_data

    def merge_nlp_modify(
        self,
        db: Session,
        existing_task: dict[str, Any],
        changed_fields: dict[str, Any],
    ) -> dict[str, Any]:
        """
        NLP modify flow.

        Input:
            existing_task: Current task data from DB
            changed_fields: Fields changed by NLP (from parse/modify)

        Returns:
            merged_task: Task with merged changes and resolved dates

        Steps:
            1. Merge changed fields with existing task
            2. Parse date strings
        """
        logger.info(f"Enrichment: merge_nlp_modify started")

        merged_task = self._change_merge(existing_task, changed_fields)

        parsed_task = self._date_parse(merged_task)

        logger.info(f"Enrichment: merge_nlp_modify complete")
        return parsed_task

    def update_task(
        self,
        db: Session,
        task_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Update task flow - recalculates computed fields.

        Input:
            task_payload: Updated task data

        Returns:
            task_with_computed: Task with recalculated urgency/value
        """
        logger.info(f"Enrichment: update_task started for '{task_payload.get('name')}'")

        task_with_computed = self._compute(task_payload)

        logger.info(
            f"Enrichment: update_task complete. Value: {task_with_computed.get('value')}"
        )
        return task_with_computed

    # ================================================================
    # HELPER: EXTRACT FIELD
    # ================================================================

    def _extract_field(self, entry: dict[str, Any]) -> Tuple[Any, bool]:
        """
        Extract value and predicted flag from {value, predicted} structure.

        Input:
            entry: {"value": ..., "predicted": bool} or just raw value

        Returns:
            (value, predicted)
        """
        if isinstance(entry, dict):
            return entry.get("value"), entry.get("predicted", False)
        return entry, False

    # ================================================================
    # HELPER: OVERWRITE DECISION
    # ================================================================

    def _get_overwrite_map(
        self,
        db: Session,
        match_result: dict[str, Any],
        nlp_payload: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """
        Determine which fields to overwrite based on predicted flags and stats.

        Priority chain:
            1. task_statistics (only if records >= 3)
            2. category_statistics (loop through categories by priority)
            3. Keep predicted value

        For duration:
            - If difficulty is predicted=True: use stats difficulty for bucket
            - If difficulty is predicted=False: use actual task_payload difficulty for bucket
        """
        overwrite_map = {}
        stats_id = match_result.get("associated_id")
        categories = self._extract_categories(nlp_payload)

        logger.debug(f"Building overwrite map. Stats ID: {stats_id}")

        # First, determine difficulty values (for duration lookup)
        difficulty_predicted = False
        difficulty_from_stats = None
        difficulty_actual = None

        if "difficulty" in nlp_payload:
            diff_value, diff_predicted = self._extract_field(nlp_payload["difficulty"])
            difficulty_predicted = diff_predicted
            difficulty_actual = diff_value

            if diff_predicted:
                # Get difficulty from stats (task or category)
                if stats_id:
                    task_stats = self._get_task_stats(db, stats_id)
                    if task_stats and task_stats.get("records", 0) >= 3:
                        difficulty_from_stats = self._get_value_from_task_stats(
                            task_stats, "difficulty"
                        )

                if difficulty_from_stats is None and categories:
                    difficulty_from_stats = self._get_value_from_category_stats(
                        db, categories, "difficulty"
                    )

        # Get deadline for importance calculation
        deadline = None
        if "deadline" in nlp_payload:
            deadline_value, _ = self._extract_field(nlp_payload["deadline"])
            if isinstance(deadline_value, datetime):
                deadline = deadline_value

        # Process each field
        fields_to_overwrite = ["difficulty", "duration", "importance", "location"]

        for field in fields_to_overwrite:
            if field not in nlp_payload:
                continue

            value, predicted = self._extract_field(nlp_payload[field])
            if not predicted:
                logger.debug(
                    f"  Field '{field}': not predicted, keeping value: {value}"
                )
                continue

            logger.debug(f"  Field '{field}': predicted=True, checking stats")

            overwrite_value = None
            overwrite_source = None

            # === TASK STATISTICS (only if records >= 3) ===
            if stats_id:
                task_stats = self._get_task_stats(db, stats_id)
                if task_stats and task_stats.get("records", 0) >= 3:
                    if field == "difficulty":
                        overwrite_value = self._get_value_from_task_stats(
                            task_stats, field
                        )
                        if overwrite_value is not None:
                            overwrite_source = "task_statistics"
                            logger.info(
                                f"    Overwriting '{field}' from task_statistics: {value} -> {overwrite_value}"
                            )

                    elif field == "duration":
                        # Determine which difficulty to use for bucket
                        if difficulty_predicted:
                            dur_difficulty = difficulty_from_stats
                        else:
                            dur_difficulty = difficulty_actual

                        if dur_difficulty is not None:
                            overwrite_value = self._get_value_from_task_stats(
                                task_stats, field, dur_difficulty
                            )
                            if overwrite_value is not None:
                                overwrite_source = "task_statistics"
                                logger.info(
                                    f"    Overwriting '{field}' from task_statistics: {value} -> {overwrite_value}"
                                )

                    elif field == "importance":
                        base_importance = value
                        overwrite_value = self._calculate_importance(
                            db, base_importance, deadline, match_result
                        )
                        if overwrite_value is not None:
                            overwrite_source = "task_statistics"
                            logger.info(
                                f"    Overwriting '{field}' from task_statistics: {value} -> {overwrite_value}"
                            )

                    elif field == "location":
                        location = self._get_location_from_task_stats(db, stats_id)
                        if location:
                            overwrite_value = location
                            overwrite_source = "task_statistics"
                            logger.info(
                                f"    Overwriting '{field}' from task_statistics: {value} -> {overwrite_value}"
                            )

            # === CATEGORY STATISTICS (if no task stats) ===
            if overwrite_value is None and categories:
                if field == "difficulty":
                    overwrite_value = self._get_value_from_category_stats(
                        db, categories, field
                    )
                    if overwrite_value is not None:
                        overwrite_source = "category_statistics"
                        logger.info(
                            f"    Overwriting '{field}' from category_statistics: {value} -> {overwrite_value}"
                        )

                elif field == "duration":
                    # Determine which difficulty to use for bucket
                    if difficulty_predicted:
                        dur_difficulty = difficulty_from_stats
                    else:
                        dur_difficulty = difficulty_actual

                    if dur_difficulty is not None:
                        overwrite_value = self._get_value_from_category_stats(
                            db, categories, field, dur_difficulty
                        )
                        if overwrite_value is not None:
                            overwrite_source = "category_statistics"
                            logger.info(
                                f"    Overwriting '{field}' from category_statistics: {value} -> {overwrite_value}"
                            )

                elif field == "importance":
                    base_importance = value
                    overwrite_value = self._calculate_importance(
                        db, base_importance, deadline, match_result
                    )
                    if overwrite_value is not None:
                        overwrite_source = "category_statistics"
                        logger.info(
                            f"    Overwriting '{field}' from category_statistics: {value} -> {overwrite_value}"
                        )

                elif field == "location":
                    location = self._get_location_from_category_stats(db, categories)
                    if location:
                        overwrite_value = location
                        overwrite_source = "category_statistics"
                        logger.info(
                            f"    Overwriting '{field}' from category_statistics: {value} -> {overwrite_value}"
                        )

            if overwrite_value is not None and overwrite_source:
                overwrite_map[field] = {
                    "source": overwrite_source,
                    "data": overwrite_value,
                }
            else:
                logger.warning(
                    f"    No stats found for '{field}', keeping predicted value: {value}"
                )

        return overwrite_map

    def _extract_categories(self, nlp_payload: dict[str, dict[str, Any]]) -> list[str]:
        """Extract category list from payload."""
        if "category" not in nlp_payload:
            return []
        value, _ = self._extract_field(nlp_payload["category"])
        if isinstance(value, list):
            return value
        return []

    def _get_task_stats(self, db: Session, stats_id: UUID) -> Optional[dict]:
        """Fetch task statistics from DB."""
        if not stats_id:
            return None
        stats = db.query(TaskStatistics).filter(TaskStatistics.id == stats_id).first()
        if stats:
            return {
                "id": stats.id,
                "avg_difficulty": stats.avg_difficulty,
                "avg_difficulty_delta": stats.avg_difficulty_delta,
                "avg_duration": stats.avg_duration,
                "avg_duration_delta": stats.avg_duration_delta,
                "records": stats.records,
                "completed_count": stats.completed_count,
                "uncompleted_count": stats.uncompleted_count,
            }
        return None

    def _calculate_bucket(self, difficulty: float) -> str:
        """Calculate difficulty bucket: round(difficulty * 2) / 2"""
        bucket = round(difficulty * 2) / 2
        return str(bucket)

    def _get_value_from_task_stats(
        self, task_stats: dict, field: str, difficulty: Optional[float] = None
    ) -> Optional[float]:
        """
        Extract difficulty or duration value from task stats.

        For difficulty: avg_difficulty + avg_difficulty_delta
        For duration: uses difficulty bucket to lookup avg_duration[bucket] + delta
        """
        if field == "difficulty":
            avg = task_stats.get("avg_difficulty")
            delta = task_stats.get("avg_difficulty_delta")
            if avg is not None:
                delta = delta if delta is not None else 0.0
                return avg + delta
        elif field == "duration":
            if difficulty is None:
                logger.warning("Duration lookup requires difficulty value")
                return None

            bucket = self._calculate_bucket(difficulty)
            duration_map = task_stats.get("avg_duration")
            duration_delta_map = task_stats.get("avg_duration_delta")

            if not duration_map:
                return None

            if bucket in duration_map:
                # Access nested structure: {"count": 5, "avg": 30}
                # Also supports old format for backward compatibility
                avg_bucket = duration_map[bucket]
                if isinstance(avg_bucket, dict):
                    avg_val = avg_bucket.get("avg")
                else:
                    # Old format: direct value
                    avg_val = avg_bucket

                # Duration delta: {"count": 3, "avg": 10}
                delta_bucket = (
                    duration_delta_map.get(bucket) if duration_delta_map else None
                )
                if isinstance(delta_bucket, dict):
                    delta_val = delta_bucket.get("avg", 0)
                else:
                    # Old format: direct value
                    delta_val = delta_bucket if delta_bucket else 0

                if avg_val is not None:
                    return avg_val + delta_val

            # Bucket not found - return None to let caller try next source
            logger.debug(f"Duration bucket '{bucket}' not found in task_stats")
            return None

        return None

    def _get_value_from_category_stats(
        self,
        db: Session,
        categories: list[str],
        field: str,
        difficulty: Optional[float] = None,
    ) -> Optional[float]:
        """
        Get value from category statistics, looping through categories by priority.

        For difficulty: avg_difficulty + avg_difficulty_delta
        For duration: uses difficulty bucket to lookup avg_duration[bucket] + delta
        """
        for category_name in categories:
            cat_stats = (
                db.query(CategoryStatistics)
                .filter(CategoryStatistics.category_name == category_name)
                .first()
            )

            if not cat_stats:
                continue

            if field == "difficulty":
                avg = cat_stats.avg_difficulty
                delta = cat_stats.avg_difficulty_delta
                if avg is not None:
                    delta = delta if delta is not None else 0.0
                    return avg + delta

            elif field == "duration":
                if difficulty is None:
                    logger.warning("Duration lookup requires difficulty value")
                    return None

                bucket = self._calculate_bucket(difficulty)
                duration_map = cat_stats.avg_duration or {}
                duration_delta_map = cat_stats.avg_duration_delta or {}

                if bucket in duration_map:
                    # Access nested structure: {"count": 5, "avg": 30}
                    # Also supports old format for backward compatibility
                    avg_bucket = duration_map[bucket]
                    if isinstance(avg_bucket, dict):
                        avg_val = avg_bucket.get("avg")
                    else:
                        # Old format: direct value
                        avg_val = avg_bucket

                    # Duration delta: {"count": 3, "avg": 10}
                    delta_bucket = (
                        duration_delta_map.get(bucket) if duration_delta_map else None
                    )
                    if isinstance(delta_bucket, dict):
                        delta_val = delta_bucket.get("avg", 0)
                    else:
                        # Old format: direct value
                        delta_val = delta_bucket if delta_bucket else 0

                    if avg_val is not None:
                        return avg_val + delta_val

                # Bucket not found in this category - continue to next category
                logger.debug(
                    f"Duration bucket '{bucket}' not found in category '{category_name}', trying next"
                )
                continue

        return None

    def _get_location_from_task_stats(
        self, db: Session, stats_id: UUID
    ) -> Optional[str]:
        """Get most frequent location from task_statistics_locations."""
        location_record = (
            db.query(TaskStatisticsLocation)
            .filter(TaskStatisticsLocation.statistics_id == stats_id)
            .order_by(desc(TaskStatisticsLocation.count))
            .first()
        )
        if location_record:
            from app.models.location import Location

            location = (
                db.query(Location)
                .filter(Location.id == location_record.location_id)
                .first()
            )
            if location:
                return location.name
        return None

    def _get_location_from_category_stats(
        self, db: Session, categories: list[str]
    ) -> Optional[str]:
        """
        Get most frequent location from category_statistics_locations.
        Loops through categories by priority.
        """
        for category_name in categories:
            cat_stats = (
                db.query(CategoryStatistics)
                .filter(CategoryStatistics.category_name == category_name)
                .first()
            )

            if not cat_stats:
                continue

            location_record = (
                db.query(CategoryStatisticsLocation)
                .filter(CategoryStatisticsLocation.statistics_id == cat_stats.id)
                .order_by(desc(CategoryStatisticsLocation.count))
                .first()
            )

            if location_record:
                from app.models.location import Location

                location = (
                    db.query(Location)
                    .filter(Location.id == location_record.location_id)
                    .first()
                )
                if location:
                    return location.name

        return None

    # ================================================================
    # HELPER: OVERWRITE FIELDS
    # ================================================================

    def _overwrite_fields(
        self,
        nlp_payload: dict[str, dict[str, Any]],
        overwrite_map: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Replace predicted fields with historical data.

        Input:
            nlp_payload: Task data with {value, predicted} structure
            overwrite_map: {field: {"source": ..., "data": ...}}

        Returns:
            task: Task with overwritten fields (flat {field: value})
        """
        result = {}

        for field, entry in nlp_payload.items():
            value, predicted = self._extract_field(entry)
            result[field] = value

        for field, config in overwrite_map.items():
            overwrite_value = config["data"]
            source = config["source"]
            del source

            if overwrite_value is not None:
                logger.info(
                    f"Overwriting '{field}': {result.get(field)} -> {overwrite_value}"
                )
                result[field] = overwrite_value

        return result

    # ================================================================
    # HELPER: IMPORTANCE CALCULATION
    # ================================================================

    def _calculate_importance(
        self,
        db: Session,
        base_importance: float,
        deadline: Optional[datetime],
        match_result: dict[str, Any],
    ) -> float:
        """
        Recalculate importance based on deadline proximity and completion rate.

        Formula:
            base = nlp_importance
            deadline_boost = 0.3 if days_left <= 1
                           = 0.2 if days_left <= 3
                           = 0.1 if days_left <= 7
                           = 0 otherwise
            completion_boost = completion_rate * 0.2
            final = min(1.0, base + deadline_boost + completion_boost)
        """
        if deadline is None:
            logger.debug("Importance: no deadline, using base")
            return base_importance

        now = datetime.utcnow()
        days_left = (deadline - now).total_seconds() / 86400

        if days_left <= 1:
            deadline_boost = 0.3
        elif days_left <= 3:
            deadline_boost = 0.2
        elif days_left <= 7:
            deadline_boost = 0.1
        else:
            deadline_boost = 0.0

        completion_rate = self._get_completion_rate(db, match_result)

        completion_boost = completion_rate * 0.2

        final_importance = min(1.0, base_importance + deadline_boost + completion_boost)

        logger.debug(
            f"Importance calculation: base={base_importance}, "
            f"days_left={days_left:.1f}, deadline_boost={deadline_boost}, "
            f"completion_rate={completion_rate}, completion_boost={completion_boost}, "
            f"final={final_importance}"
        )

        return round(final_importance, 4)

    def _get_completion_rate(
        self,
        db: Session,
        match_result: dict[str, Any],
    ) -> float:
        """
        Get completion rate from task or category statistics.

        Returns:
            completion_rate = completed_count / (completed_count + uncompleted_count)
            - From matched task if (completed_count + uncompleted_count) >= 3
            - From category statistics otherwise
            - 0.5 default if no data
        """
        stats_id = match_result.get("associated_id")
        status = match_result.get("association_status", "none")

        if stats_id and status in ("same", "similar"):
            task_stats = self._get_task_stats(db, stats_id)
            if task_stats:
                total = task_stats["completed_count"] + task_stats["uncompleted_count"]
                if total >= 3:
                    completed = task_stats["completed_count"]
                    rate = completed / total if total > 0 else 0.5
                    logger.debug(f"Completion rate from task_stats: {rate}")
                    return rate

        logger.debug("No task stats or insufficient data, checking category stats")
        return 0.5

    # ================================================================
    # HELPER: INTERNAL REFS
    # ================================================================

    def _add_internal_refs(
        self,
        task_data: dict[str, Any],
        match_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Add internal references to task data."""
        result = task_data.copy()
        result["task_statistics_id"] = match_result.get("associated_id")
        result["name_vector"] = match_result.get("name_vector")
        result["association_status"] = match_result.get("association_status")
        return result

    # ================================================================
    # HELPER: DATE PARSING
    # ================================================================

    def _date_parse(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Parse date strings to datetime objects.

        Input:
            task: Task data (may have raw string dates)

        Returns:
            task: Task with datetime objects for date fields
        """
        result = task.copy()
        date_fields = ["start", "deadline", "fixed_start"]

        for field in date_fields:
            value = result.get(field)
            if isinstance(value, str) and value:
                parsed = self._parse_date_string(value)
                if parsed:
                    result[field] = parsed
                    logger.debug(f"Parsed {field}: '{value}' -> {parsed}")
                else:
                    logger.warning(f"Failed to parse {field}: '{value}'")
                    result[field] = None

        return result

    def _parse_date_string(self, date_string: str) -> Optional[datetime]:
        """Parse a date string using dateparser."""
        try:
            parsed = dateparser.parse(date_string)
            if parsed:
                return parsed
        except Exception as e:
            logger.error(f"Date parsing error: {e}")
        return None

    # ================================================================
    # HELPER: DRAFT OPERATIONS
    # ================================================================

    def _draft_save(
        self,
        db: Session,
        task_payload: dict[str, Any],
        match_result: dict[str, Any],
    ) -> UUID:
        """
        Save task to draft table.

        Input:
            task_payload: Enriched task data
            match_result: Task matching result

        Returns:
            draft_id: UUID of saved draft
        """
        draft_id = uuid4()

        content = {
            "task": task_payload,
            "match_result": {
                "associated_id": str(match_result.get("associated_id"))
                if match_result.get("associated_id")
                else None,
                "association_status": match_result.get("association_status"),
                "name_vector": match_result.get("name_vector"),
            },
        }

        draft = TaskDraft(id=draft_id, content=content)
        db.add(draft)
        db.commit()

        logger.info(f"Draft saved: {draft_id}")
        return draft_id

    def _draft_load(self, db: Session, draft_id: UUID) -> Optional[dict[str, Any]]:
        """Load task from draft table and delete it."""
        draft = db.query(TaskDraft).filter(TaskDraft.id == draft_id).first()
        if draft:
            content = draft.content
            logger.debug(f"Draft loaded: {draft_id}")

            # Delete draft after loading (memory efficiency)
            db.delete(draft)
            db.commit()
            logger.info(f"Draft deleted: {draft_id}")

            return content
        logger.warning(f"Draft not found: {draft_id}")
        return None

    def _draft_merge(
        self,
        request_task: dict[str, Any],
        draft_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Merge request task with draft (request priority).

        Request fields take precedence over draft fields.
        """
        if not draft_data:
            logger.debug("No draft data, using request only")
            return request_task

        draft_task = draft_data.get("task", {})

        merged = draft_task.copy()
        for key, value in request_task.items():
            if value is not None:
                merged[key] = value
            elif key not in merged:
                merged[key] = None

        logger.debug("Merged request with draft (request priority)")
        return merged

    # ================================================================
    # HELPER: CHANGE MERGE (for NLP modify)
    # ================================================================

    def _change_merge(
        self,
        existing_task: dict[str, Any],
        changed_fields: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Merge NLP changed fields with existing task.

        Changed fields take precedence over existing fields.
        """
        merged = existing_task.copy()
        for key, value in changed_fields.items():
            if value is not None:
                merged[key] = value

        logger.debug("Merged NLP changes with existing task")
        return merged

    # ================================================================
    # HELPER: COMPUTE (urgency/value)
    # ================================================================

    def _compute(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Calculate derived fields: urgency, value, and importance (if predicted).

        Input:
            task: Task with importance, deadline, difficulty

        Returns:
            task: Task with added urgency, value, and possibly updated importance
        """
        result = task.copy()

        importance = result.get("importance", 0.5)
        deadline = result.get("deadline")
        difficulty = result.get("difficulty", 0.5)

        urgency = self._calculate_urgency(importance, deadline)
        value = self._calculate_value(importance, urgency, difficulty)

        result["urgency"] = urgency
        result["value"] = value

        logger.debug(f"Computed: urgency={urgency}, value={value}")
        return result

    @staticmethod
    def _calculate_urgency(importance: float, deadline: Optional[datetime]) -> float:
        """
        Calculate urgency: min(1.0, importance * (1/days_left) * 3)

        Uses total_seconds for sub-day precision.
        """
        if not deadline:
            return 0.0

        now = datetime.utcnow()
        days_left = (deadline - now).total_seconds() / 86400

        if days_left <= 0:
            days_left = 0.001

        urgency = min(1.0, importance * (1 / days_left) * 3)
        return round(max(0.0, urgency), 4)

    @staticmethod
    def _calculate_value(
        importance: float,
        urgency: float,
        difficulty: float,
        completion_rate: float = 1.0,
    ) -> float:
        """
        Calculate composite value.

        Formula: (importance * 0.4 + urgency * 0.4 + difficulty * 0.2) * completion_rate
        """
        raw_value = (importance * 0.4) + (urgency * 0.4) + (difficulty * 0.2)
        return round(raw_value * completion_rate, 4)


enrichment_service = EnrichmentService()
