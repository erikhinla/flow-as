"""
Agent Zero Review Enforcement Service

Ensures high-risk tasks cannot execute without:
1. task.diff - unified diff of proposed changes
2. task.review.md - review document with approver signature
3. task.rollback.md - rollback plan if deployment fails

All three artifacts must exist and be valid before execution.
"""

import logging
import re
from datetime import datetime
from typing import Tuple, Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class ReviewArtifact:
    """Base class for review artifacts"""
    
    def __init__(self, content: str, job_id: str, artifact_type: str):
        self.content = content
        self.job_id = job_id
        self.artifact_type = artifact_type  # diff, review, rollback
        self.created_at = datetime.utcnow()
    
    def save_to_disk(self, base_path: str = "runtime/reviews") -> str:
        """Save artifact to disk and return path"""
        artifact_dir = Path(base_path) / self.job_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = artifact_dir / f"task.{self.artifact_type}"
        with open(file_path, 'w') as f:
            f.write(self.content)
        
        logger.info(f"Saved {self.artifact_type} artifact: {file_path}")
        return str(file_path)
    
    @staticmethod
    def load_from_disk(job_id: str, artifact_type: str, base_path: str = "runtime/reviews") -> Optional[str]:
        """Load artifact from disk"""
        file_path = Path(base_path) / job_id / f"task.{artifact_type}"
        
        if not file_path.exists():
            logger.warning(f"Artifact not found: {file_path}")
            return None
        
        with open(file_path, 'r') as f:
            return f.read()


class DiffArtifact(ReviewArtifact):
    """
    Unified diff artifact showing proposed changes.
    
    Format:
    --- a/path/to/file
    +++ b/path/to/file
    @@ -10,5 +10,8 @@
     existing line
    -removed line
    +added line
    """
    
    def __init__(self, content: str, job_id: str):
        super().__init__(content, job_id, "diff")
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate diff format and content.
        
        Returns:
            (bool, error_message)
        """
        
        if not self.content or len(self.content.strip()) == 0:
            return False, "Diff is empty"
        
        # Check for unified diff markers
        has_header = bool(re.search(r'^---\s+a/', self.content, re.MULTILINE))
        has_content = bool(re.search(r'^[\+\-\@]', self.content, re.MULTILINE))
        
        if not (has_header and has_content):
            return False, "Diff does not appear to be in unified diff format"
        
        # Check for suspicious patterns (binary files, too large)
        lines = self.content.split('\n')
        if len(lines) > 10000:
            return False, f"Diff too large ({len(lines)} lines). Consider breaking into smaller changes."
        
        logger.info(f"Diff validated: {len(lines)} lines, multiple files")
        return True, None
    
    def get_files_changed(self) -> list:
        """Extract list of files changed from diff"""
        files = []
        for line in self.content.split('\n'):
            if line.startswith('--- a/'):
                file_path = line[6:].strip()
                if file_path not in files:
                    files.append(file_path)
        return files


class ReviewArtifact_(ReviewArtifact):
    """
    Review document with approver signature.
    
    Required sections:
    - What changed
    - Why
    - Impact
    - Testing
    - Rollback
    - Risks
    - Approver (signature + date)
    """
    
    REQUIRED_SECTIONS = [
        'What changed',
        'Why',
        'Impact',
        'Testing',
        'Rollback',
        'Risks',
        'Approver'
    ]
    
    def __init__(self, content: str, job_id: str):
        super().__init__(content, job_id, "review")
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate review document format and approver signature.
        
        Returns:
            (bool, error_message)
        """
        
        if not self.content or len(self.content.strip()) < 50:
            return False, "Review document too short or empty"
        
        # Check for required sections
        missing_sections = []
        for section in self.REQUIRED_SECTIONS:
            if section.lower() not in self.content.lower():
                missing_sections.append(section)
        
        if missing_sections:
            return False, f"Review missing required sections: {', '.join(missing_sections)}"
        
        # Check for approver signature (name + date)
        approver_pattern = r'Approver:\s+(\w+[\w\s]*\w+)\s*,?\s*(\d{4}-\d{2}-\d{2})'
        if not re.search(approver_pattern, self.content):
            return False, "Review missing approver signature and date (format: 'Approver: Name, YYYY-MM-DD')"
        
        logger.info(f"Review document validated with approver signature")
        return True, None
    
    def get_approver(self) -> Tuple[Optional[str], Optional[str]]:
        """Extract approver name and date"""
        approver_pattern = r'Approver:\s+(\w+[\w\s]*\w+)\s*,?\s*(\d{4}-\d{2}-\d{2})'
        match = re.search(approver_pattern, self.content)
        
        if match:
            name = match.group(1).strip()
            date = match.group(2).strip()
            return name, date
        
        return None, None


class RollbackArtifact(ReviewArtifact):
    """
    Rollback plan artifact.
    
    Required sections:
    - Detection (how to know if rollback is needed)
    - Immediate Actions (steps to take)
    - Validation (confirm rollback worked)
    """
    
    REQUIRED_SECTIONS = [
        'Detection',
        'Immediate Actions',
        'Validation'
    ]
    
    def __init__(self, content: str, job_id: str):
        super().__init__(content, job_id, "rollback")
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate rollback plan format.
        
        Returns:
            (bool, error_message)
        """
        
        if not self.content or len(self.content.strip()) < 50:
            return False, "Rollback plan too short or empty"
        
        # Check for required sections
        missing_sections = []
        for section in self.REQUIRED_SECTIONS:
            if section.lower() not in self.content.lower():
                missing_sections.append(section)
        
        if missing_sections:
            return False, f"Rollback plan missing sections: {', '.join(missing_sections)}"
        
        # Check for specific, actionable steps (not vague)
        if 'TODO' in self.content or 'TBD' in self.content:
            return False, "Rollback plan contains TODO/TBD - must be complete and specific"
        
        logger.info(f"Rollback plan validated with detection and actions")
        return True, None


class ReviewEnforcementService:
    """
    Gate high-risk task execution behind review artifacts.
    
    Before Agent Zero executes, all three artifacts must:
    1. Exist (on disk or in database)
    2. Pass validation (format, completeness, signatures)
    3. Be approved (approver signature present)
    """
    
    @staticmethod
    async def check_review_artifacts(job_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if all required review artifacts exist and are valid.
        
        Returns:
            (all_present_and_valid, artifacts_status)
        """
        
        status = {
            'diff': {'present': False, 'valid': False, 'error': None},
            'review': {'present': False, 'valid': False, 'error': None, 'approver': None},
            'rollback': {'present': False, 'valid': False, 'error': None},
        }
        
        # Check diff
        diff_content = ReviewArtifact.load_from_disk(job_id, 'diff')
        if diff_content:
            status['diff']['present'] = True
            diff = DiffArtifact(diff_content, job_id)
            valid, error = diff.validate()
            status['diff']['valid'] = valid
            if error:
                status['diff']['error'] = error
        else:
            status['diff']['error'] = "Diff artifact not found"
        
        # Check review
        review_content = ReviewArtifact.load_from_disk(job_id, 'review')
        if review_content:
            status['review']['present'] = True
            review = ReviewArtifact_(review_content, job_id)
            valid, error = review.validate()
            status['review']['valid'] = valid
            if error:
                status['review']['error'] = error
            else:
                approver_name, approver_date = review.get_approver()
                status['review']['approver'] = {'name': approver_name, 'date': approver_date}
        else:
            status['review']['error'] = "Review document not found"
        
        # Check rollback
        rollback_content = ReviewArtifact.load_from_disk(job_id, 'rollback')
        if rollback_content:
            status['rollback']['present'] = True
            rollback = RollbackArtifact(rollback_content, job_id)
            valid, error = rollback.validate()
            status['rollback']['valid'] = valid
            if error:
                status['rollback']['error'] = error
        else:
            status['rollback']['error'] = "Rollback plan not found"
        
        # Determine overall status
        all_valid = all(status[k]['valid'] for k in status)
        
        logger.info(f"Review artifacts check for {job_id}: all_valid={all_valid}, status={status}")
        
        return all_valid, status
    
    @staticmethod
    async def block_if_missing_artifacts(job_id: str) -> Tuple[bool, Optional[str]]:
        """
        Block execution if any review artifacts are missing.
        
        Called by Agent Zero before execution.
        
        Returns:
            (can_execute, error_message)
        """
        
        all_valid, status = await ReviewEnforcementService.check_review_artifacts(job_id)
        
        if not all_valid:
            # Build error message
            missing = []
            for artifact_type in ['diff', 'review', 'rollback']:
                if not status[artifact_type]['present']:
                    missing.append(f"task.{artifact_type}")
            
            invalid = []
            for artifact_type in ['diff', 'review', 'rollback']:
                if status[artifact_type]['present'] and not status[artifact_type]['valid']:
                    error = status[artifact_type]['error']
                    invalid.append(f"task.{artifact_type}: {error}")
            
            error_msg = "Cannot execute without complete review artifacts. "
            if missing:
                error_msg += f"Missing: {', '.join(missing)}. "
            if invalid:
                error_msg += f"Invalid: {'; '.join(invalid)}."
            
            logger.error(f"Blocking execution of {job_id}: {error_msg}")
            return False, error_msg
        
        logger.info(f"All review artifacts valid for {job_id}, execution allowed")
        return True, None
    
    @staticmethod
    async def save_artifacts(
        job_id: str,
        diff_content: str,
        review_content: str,
        rollback_content: str
    ) -> Dict[str, str]:
        """
        Save all review artifacts to disk.
        
        Returns:
            {artifact_type: file_path}
        """
        
        artifacts = {}
        
        try:
            diff = DiffArtifact(diff_content, job_id)
            artifacts['diff'] = diff.save_to_disk()
            
            review = ReviewArtifact_(review_content, job_id)
            artifacts['review'] = review.save_to_disk()
            
            rollback = RollbackArtifact(rollback_content, job_id)
            artifacts['rollback'] = rollback.save_to_disk()
            
            logger.info(f"All review artifacts saved for {job_id}")
            return artifacts
        
        except Exception as e:
            logger.error(f"Error saving artifacts for {job_id}: {e}", exc_info=True)
            raise
