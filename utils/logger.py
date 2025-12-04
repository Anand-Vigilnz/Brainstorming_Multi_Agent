"""Centralized logging utility for tracking agent communications."""
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class AgentLogger:
    """Logger for tracking agent-to-agent communications."""
    
    def __init__(self, agent_name: str, log_dir: str = "logs"):
        """
        Initialize the logger for an agent.
        
        Args:
            agent_name: Name of the agent (e.g., "host_agent", "idea_agent")
            log_dir: Directory to store log files
        """
        self.agent_name = agent_name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create separate log files for different purposes
        self.communication_log_file = self.log_dir / f"{agent_name}_communications.jsonl"
        self.error_log_file = self.log_dir / f"{agent_name}_errors.log"
        self.activity_log_file = self.log_dir / f"{agent_name}_activity.log"
        
        # Set up standard Python logger for errors and activity
        self.logger = logging.getLogger(f"{agent_name}_logger")
        self.logger.setLevel(logging.INFO)
        
        # File handler for errors
        error_handler = logging.FileHandler(self.error_log_file)
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        error_handler.setFormatter(error_formatter)
        
        # File handler for activity
        activity_handler = logging.FileHandler(self.activity_log_file)
        activity_handler.setLevel(logging.INFO)
        activity_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        activity_handler.setFormatter(activity_formatter)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        self.logger.addHandler(error_handler)
        self.logger.addHandler(activity_handler)
        self.logger.addHandler(console_handler)
    
    def log_request(
        self,
        to_agent: str,
        skill: str,
        request_data: Dict[str, Any],
        request_id: Optional[str] = None
    ):
        """
        Log an outgoing request to another agent.
        
        Args:
            to_agent: Name of the target agent
            skill: Skill being requested
            request_data: Request payload
            request_id: Optional unique request ID for tracking
        """
        if not request_id:
            request_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{self.agent_name}_{to_agent}"
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "request",
            "request_id": request_id,
            "from_agent": self.agent_name,
            "to_agent": to_agent,
            "skill": skill,
            "request_data": request_data,
            "status": "sent"
        }
        
        self._write_communication_log(log_entry)
        self.logger.info(
            f"REQUEST [{request_id}] {self.agent_name} -> {to_agent} | Skill: {skill}"
        )
    
    def log_response(
        self,
        from_agent: str,
        skill: str,
        request_id: Optional[str],
        response_data: Dict[str, Any],
        status: str = "success",
        error: Optional[str] = None
    ):
        """
        Log an incoming response from another agent.
        
        Args:
            from_agent: Name of the source agent
            skill: Skill that was requested
            request_id: Request ID from the original request
            response_data: Response payload
            status: Response status (success, error)
            error: Error message if status is error
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "response",
            "request_id": request_id,
            "from_agent": from_agent,
            "to_agent": self.agent_name,
            "skill": skill,
            "response_data": response_data,
            "status": status,
            "error": error
        }
        
        self._write_communication_log(log_entry)
        
        if status == "error":
            self.logger.error(
                f"RESPONSE [{request_id}] {from_agent} -> {self.agent_name} | Skill: {skill} | ERROR: {error}"
            )
        else:
            self.logger.info(
                f"RESPONSE [{request_id}] {from_agent} -> {self.agent_name} | Skill: {skill} | Status: {status}"
            )
    
    def log_incoming_request(
        self,
        from_agent: str,
        skill: str,
        request_data: Dict[str, Any],
        request_id: Optional[str] = None
    ):
        """
        Log an incoming request from another agent.
        
        Args:
            from_agent: Name of the source agent
            skill: Skill being requested
            request_data: Request payload
            request_id: Optional unique request ID
        """
        if not request_id:
            request_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{from_agent}_{self.agent_name}"
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "incoming_request",
            "request_id": request_id,
            "from_agent": from_agent,
            "to_agent": self.agent_name,
            "skill": skill,
            "request_data": request_data,
            "status": "received"
        }
        
        self._write_communication_log(log_entry)
        self.logger.info(
            f"INCOMING REQUEST [{request_id}] {from_agent} -> {self.agent_name} | Skill: {skill}"
        )
        return request_id
    
    def log_outgoing_response(
        self,
        to_agent: str,
        skill: str,
        request_id: Optional[str],
        response_data: Dict[str, Any],
        status: str = "success",
        error: Optional[str] = None
    ):
        """
        Log an outgoing response to another agent.
        
        Args:
            to_agent: Name of the target agent
            skill: Skill that was requested
            request_id: Request ID from the original request
            response_data: Response payload
            status: Response status (success, error)
            error: Error message if status is error
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "outgoing_response",
            "request_id": request_id,
            "from_agent": self.agent_name,
            "to_agent": to_agent,
            "skill": skill,
            "response_data": response_data,
            "status": status,
            "error": error
        }
        
        self._write_communication_log(log_entry)
        
        if status == "error":
            self.logger.error(
                f"OUTGOING RESPONSE [{request_id}] {self.agent_name} -> {to_agent} | Skill: {skill} | ERROR: {error}"
            )
        else:
            self.logger.info(
                f"OUTGOING RESPONSE [{request_id}] {self.agent_name} -> {to_agent} | Skill: {skill} | Status: {status}"
            )
    
    def log_error(self, message: str, error: Exception, context: Optional[Dict[str, Any]] = None):
        """
        Log an error with context.
        
        Args:
            message: Error message
            error: Exception object
            context: Additional context information
        """
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent_name,
            "message": message,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }
        
        self.logger.error(f"{message}: {str(error)}", exc_info=True)
        
        # Also log to communication log for tracking
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "error",
            "agent": self.agent_name,
            "message": message,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }
        self._write_communication_log(log_entry)
    
    def log_activity(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Log general activity.
        
        Args:
            message: Activity message
            details: Additional details
        """
        self.logger.info(message)
        if details:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "type": "activity",
                "agent": self.agent_name,
                "message": message,
                "details": details
            }
            self._write_communication_log(log_entry)
    
    def _write_communication_log(self, log_entry: Dict[str, Any]):
        """Write a log entry to the JSONL communication log file."""
        try:
            with open(self.communication_log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write communication log: {str(e)}")
    
    def get_communication_logs(self, limit: Optional[int] = None) -> list:
        """
        Read communication logs.
        
        Args:
            limit: Maximum number of log entries to return
            
        Returns:
            List of log entries
        """
        logs = []
        try:
            if self.communication_log_file.exists():
                with open(self.communication_log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            logs.append(json.loads(line))
                if limit:
                    logs = logs[-limit:]
        except Exception as e:
            self.logger.error(f"Failed to read communication logs: {str(e)}")
        return logs

