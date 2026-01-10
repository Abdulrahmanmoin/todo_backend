from sqlmodel import select, Session, and_
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from backend.src.models.task import Task, TaskCreate, TaskUpdate, TaskUpdateStatus
from backend.src.models.user import User


class TaskService:
    """Service class for handling task operations with user isolation"""

    @staticmethod
    def create_task(*, db_session: Session, task_in: TaskCreate, user_id: UUID) -> Task:
        """
        Create a new task for the specified user

        Args:
            db_session: Database session
            task_in: Task creation data
            user_id: ID of the user creating the task

        Returns:
            Created Task object
        """
        # Create task with the specified user_id
        task = Task(
            **task_in.dict(),
            user_id=user_id
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        return task

    @staticmethod
    def get_task_by_id(*, db_session: Session, task_id: UUID, user_id: UUID) -> Optional[Task]:
        """
        Retrieve a specific task by ID for the specified user

        Args:
            db_session: Database session
            task_id: ID of the task to retrieve
            user_id: ID of the user requesting the task

        Returns:
            Task object if found and belongs to user, None otherwise
        """
        # Ensure user can only access their own tasks
        statement = select(Task).where(
            and_(Task.task_id == task_id, Task.user_id == user_id)
        )
        task = db_session.exec(statement).first()
        return task

    @staticmethod
    def get_tasks_by_user(*, db_session: Session, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Task]:
        """
        Retrieve all tasks for the specified user

        Args:
            db_session: Database session
            user_id: ID of the user whose tasks to retrieve
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Task objects belonging to the user
        """
        statement = select(Task).where(Task.user_id == user_id).offset(skip).limit(limit)
        tasks = db_session.exec(statement).all()
        return tasks

    @staticmethod
    def update_task(*, db_session: Session, task_id: UUID, task_in: TaskUpdate, user_id: UUID) -> Optional[Task]:
        """
        Update a specific task for the specified user

        Args:
            db_session: Database session
            task_id: ID of the task to update
            task_in: Task update data
            user_id: ID of the user requesting the update

        Returns:
            Updated Task object if found and belongs to user, None otherwise
        """
        # Get the existing task for the user
        statement = select(Task).where(
            and_(Task.task_id == task_id, Task.user_id == user_id)
        )
        task = db_session.exec(statement).first()

        if not task:
            return None

        # Update the task with provided values
        update_data = task_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)

        # If task is being marked as completed, set completed_at timestamp
        if update_data.get('is_completed') is True and task.is_completed != True:
            task.completed_at = datetime.utcnow()
        # If task is being marked as not completed, clear completed_at timestamp
        elif update_data.get('is_completed') is False:
            task.completed_at = None

        task.updated_at = datetime.utcnow()
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        return task

    @staticmethod
    def update_task_status(*, db_session: Session, task_id: UUID, status_in: TaskUpdateStatus, user_id: UUID) -> Optional[Task]:
        """
        Update the completion status of a specific task for the specified user

        Args:
            db_session: Database session
            task_id: ID of the task to update
            status_in: Task status update data
            user_id: ID of the user requesting the update

        Returns:
            Updated Task object if found and belongs to user, None otherwise
        """
        # Get the existing task for the user
        statement = select(Task).where(
            and_(Task.task_id == task_id, Task.user_id == user_id)
        )
        task = db_session.exec(statement).first()

        if not task:
            return None

        # Update the completion status
        task.is_completed = status_in.is_completed

        # Set completed_at timestamp if being marked as completed
        if status_in.is_completed:
            task.completed_at = datetime.utcnow()
        else:
            task.completed_at = None

        task.updated_at = datetime.utcnow()
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        return task

    @staticmethod
    def delete_task(*, db_session: Session, task_id: UUID, user_id: UUID) -> bool:
        """
        Delete a specific task for the specified user

        Args:
            db_session: Database session
            task_id: ID of the task to delete
            user_id: ID of the user requesting the deletion

        Returns:
            True if task was deleted, False if not found or doesn't belong to user
        """
        # Get the task for the user
        statement = select(Task).where(
            and_(Task.task_id == task_id, Task.user_id == user_id)
        )
        task = db_session.exec(statement).first()

        if not task:
            return False

        db_session.delete(task)
        db_session.commit()
        return True

    @staticmethod
    def get_user_completed_tasks(*, db_session: Session, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Task]:
        """
        Retrieve completed tasks for the specified user

        Args:
            db_session: Database session
            user_id: ID of the user whose completed tasks to retrieve
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of completed Task objects belonging to the user
        """
        statement = select(Task).where(
            and_(Task.user_id == user_id, Task.is_completed == True)
        ).offset(skip).limit(limit)
        tasks = db_session.exec(statement).all()
        return tasks

    @staticmethod
    def get_user_pending_tasks(*, db_session: Session, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Task]:
        """
        Retrieve pending tasks for the specified user

        Args:
            db_session: Database session
            user_id: ID of the user whose pending tasks to retrieve
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of pending Task objects belonging to the user
        """
        statement = select(Task).where(
            and_(Task.user_id == user_id, Task.is_completed == False)
        ).offset(skip).limit(limit)
        tasks = db_session.exec(statement).all()
        return tasks