from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
from typing import List
import uuid

from ..database import get_async_session
from ..models import Task, TaskCreate, TaskRead, TaskUpdate, User
from ..utils.auth import get_current_user


router = APIRouter()


@router.post("/{user_id}/tasks", response_model=TaskRead)
async def create_task(
    user_id: uuid.UUID,
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Create a new task for a specific user.

    This endpoint allows authenticated users to create a new task associated with a specific user ID.
    Users can only create tasks for themselves unless they have admin privileges (not implemented in this version).

    Args:
        user_id: UUID of the user for whom to create the task
        task_data: Task creation data including title and optional description
        current_user: The authenticated user making the request
        session: Database session for creating the task

    Returns:
        TaskRead: The created task with all its details

    Raises:
        HTTPException: 400 if task data is invalid
        HTTPException: 403 if user doesn't have permission to create tasks for this user_id
        HTTPException: 500 if an error occurs during task creation
    """
    try:
        # Validate that the requesting user has permission to create tasks for this user_id
        if current_user.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create tasks for this user"
            )

        # Create a new task instance with the provided data and user_id
        task = Task(
            user_id=user_id,
            title=task_data.title,
            description=task_data.description,
            is_completed=task_data.is_completed  # This defaults to False if not provided
        )

        # Add the task to the session and commit it to the database
        session.add(task)
        await session.commit()
        await session.refresh(task)  # Refresh to get the auto-generated fields like task_id

        # Return the created task
        return task

    except HTTPException:
        # Re-raise HTTP exceptions to maintain proper error handling
        raise
    except Exception as e:
        # Log internal errors for debugging
        print(f"Error creating task: {str(e)}")  # In production, use proper logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the task"
        )


@router.get("/{user_id}/tasks", response_model=List[TaskRead])
async def get_user_tasks(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Retrieve all tasks for a specific user.

    This endpoint allows authenticated users to retrieve all tasks associated with a specific user ID.
    Users can only access their own tasks unless they have admin privileges (not implemented in this version).

    Args:
        user_id: UUID of the user whose tasks to retrieve
        current_user: The authenticated user making the request
        session: Database session for querying tasks

    Returns:
        List[TaskRead]: A list of tasks belonging to the specified user

    Raises:
        HTTPException: 403 if user doesn't have permission to access these tasks
        HTTPException: 500 if an error occurs during retrieval
    """
    try:
        # Check if the requesting user is trying to access their own tasks
        # In a future enhancement, we could add admin role checking
        if current_user.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access tasks for this user"
            )

        # Query tasks for the specified user
        tasks = await session.exec(
            select(Task).where(Task.user_id == user_id)
        )

        user_tasks = tasks.all()

        # Return the list of tasks (can be empty if no tasks exist)
        return user_tasks

    except HTTPException:
        # Re-raise HTTP exceptions to maintain proper error handling
        raise
    except Exception as e:
        # Log internal errors for debugging
        print(f"Error retrieving user tasks: {str(e)}")  # In production, use proper logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving tasks"
        )


@router.get("/{user_id}/tasks/{id}", response_model=TaskRead)
async def get_task(
    user_id: uuid.UUID,
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Retrieve a specific task for a user.

    This endpoint allows authenticated users to retrieve a specific task associated with a user ID.
    Users can only access their own tasks unless they have admin privileges (not implemented in this version).

    Args:
        user_id: UUID of the user who owns the task
        id: UUID of the specific task to retrieve
        current_user: The authenticated user making the request
        session: Database session for querying the task

    Returns:
        TaskRead: The requested task with all its details

    Raises:
        HTTPException: 403 if user doesn't have permission to access this task
        HTTPException: 404 if the task doesn't exist
        HTTPException: 500 if an error occurs during retrieval
    """
    try:
        # Validate that the requesting user has permission to access tasks for this user_id
        if current_user.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access tasks for this user"
            )

        # Query the specific task by ID and user_id to ensure data isolation
        task = await session.exec(
            select(Task).where(Task.task_id == id, Task.user_id == user_id)
        )
        task = task.first()

        # Check if the task exists
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Return the task
        return task

    except HTTPException:
        # Re-raise HTTP exceptions to maintain proper error handling
        raise
    except Exception as e:
        # Log internal errors for debugging
        print(f"Error retrieving task: {str(e)}")  # In production, use proper logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the task"
        )


@router.put("/{user_id}/tasks/{id}", response_model=TaskRead)
async def update_task(
    user_id: uuid.UUID,
    id: uuid.UUID,
    task_data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Update a specific task for a user.

    This endpoint allows authenticated users to update a specific task associated with a user ID.
    Users can only update their own tasks unless they have admin privileges (not implemented in this version).

    Args:
        user_id: UUID of the user who owns the task
        id: UUID of the specific task to update
        task_data: Task update data with fields to modify
        current_user: The authenticated user making the request
        session: Database session for updating the task

    Returns:
        TaskRead: The updated task with all its details

    Raises:
        HTTPException: 403 if user doesn't have permission to update this task
        HTTPException: 404 if the task doesn't exist
        HTTPException: 400 if the task data is invalid
        HTTPException: 500 if an error occurs during update
    """
    try:
        # Validate that the requesting user has permission to update tasks for this user_id
        if current_user.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update tasks for this user"
            )

        # Query the specific task by ID and user_id to ensure data isolation
        task = await session.exec(
            select(Task).where(Task.task_id == id, Task.user_id == user_id)
        )
        task = task.first()

        # Check if the task exists
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Update task fields with provided data, only if they are not None
        update_data = task_data.dict(exclude_unset=True)

        # Handle completion status update
        for field, value in update_data.items():
            setattr(task, field, value)

        # If is_completed is being set to True and completed_at is not set, set it to now
        if hasattr(task_data, 'is_completed') and task_data.is_completed and task.completed_at is None:
            task.completed_at = datetime.utcnow()
        # If is_completed is being set to False, clear completed_at
        elif hasattr(task_data, 'is_completed') and not task_data.is_completed:
            task.completed_at = None

        # Update the updated_at timestamp
        task.updated_at = datetime.utcnow()

        # Commit changes to the database
        await session.commit()
        await session.refresh(task)  # Refresh to get the updated task with new timestamps

        # Return the updated task
        return task

    except HTTPException:
        # Re-raise HTTP exceptions to maintain proper error handling
        raise
    except Exception as e:
        # Log internal errors for debugging
        print(f"Error updating task: {str(e)}")  # In production, use proper logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the task"
        )


@router.delete("/{user_id}/tasks/{id}")
async def delete_task(
    user_id: uuid.UUID,
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Delete a specific task for a user.

    This endpoint allows authenticated users to delete a specific task associated with a user ID.
    Users can only delete their own tasks unless they have admin privileges (not implemented in this version).

    Args:
        user_id: UUID of the user who owns the task
        id: UUID of the specific task to delete
        current_user: The authenticated user making the request
        session: Database session for deleting the task

    Returns:
        dict: Success message confirming the deletion

    Raises:
        HTTPException: 403 if user doesn't have permission to delete this task
        HTTPException: 404 if the task doesn't exist
        HTTPException: 500 if an error occurs during deletion
    """
    try:
        # Validate that the requesting user has permission to delete tasks for this user_id
        if current_user.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete tasks for this user"
            )

        # Query the specific task by ID and user_id to ensure data isolation
        task = await session.exec(
            select(Task).where(Task.task_id == id, Task.user_id == user_id)
        )
        task = task.first()

        # Check if the task exists
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Delete the task from the database
        await session.delete(task)
        await session.commit()

        # Return success message
        return {"message": "Task deleted successfully"}

    except HTTPException:
        # Re-raise HTTP exceptions to maintain proper error handling
        raise
    except Exception as e:
        # Log internal errors for debugging
        print(f"Error deleting task: {str(e)}")  # In production, use proper logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the task"
        )


@router.patch("/{user_id}/tasks/{id}/complete", response_model=TaskRead)
async def update_task_completion(
    user_id: uuid.UUID,
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """
    Update the completion status of a specific task for a user.

    This endpoint allows authenticated users to toggle the completion status of a specific task.
    Users can only update their own tasks unless they have admin privileges (not implemented in this version).

    Args:
        user_id: UUID of the user who owns the task
        id: UUID of the specific task to update completion status
        current_user: The authenticated user making the request
        session: Database session for updating the task

    Returns:
        TaskRead: The updated task with the new completion status

    Raises:
        HTTPException: 403 if user doesn't have permission to update this task
        HTTPException: 404 if the task doesn't exist
        HTTPException: 500 if an error occurs during update
    """
    try:
        # Validate that the requesting user has permission to update tasks for this user_id
        if current_user.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update tasks for this user"
            )

        # Query the specific task by ID and user_id to ensure data isolation
        task = await session.exec(
            select(Task).where(Task.task_id == id, Task.user_id == user_id)
        )
        task = task.first()

        # Check if the task exists
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )

        # Toggle the completion status
        new_completion_status = not task.is_completed
        task.is_completed = new_completion_status

        # Set completed_at timestamp based on the new status
        if new_completion_status:
            # Task is being marked as completed
            from datetime import datetime
            task.completed_at = datetime.utcnow()
        else:
            # Task is being marked as incomplete
            task.completed_at = None

        # Update the updated_at timestamp
        task.updated_at = datetime.utcnow()

        # Commit changes to the database
        await session.commit()
        await session.refresh(task)  # Refresh to get the updated task with new timestamps

        # Return the updated task
        return task

    except HTTPException:
        # Re-raise HTTP exceptions to maintain proper error handling
        raise
    except Exception as e:
        # Log internal errors for debugging
        print(f"Error updating task completion: {str(e)}")  # In production, use proper logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the task completion status"
        )