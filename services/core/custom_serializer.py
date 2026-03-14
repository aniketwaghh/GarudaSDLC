"""
Custom serializer for LangGraph checkpointer that handles unpicklable objects.
This is needed because some middleware objects contain threading locks that cannot be pickled.
"""
from typing import Any, Tuple
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
import pickle
import logging

logger = logging.getLogger(__name__)


class CustomSerializer(JsonPlusSerializer):
    """
    Custom serializer that extends JsonPlusSerializer to handle unpicklable objects
    from middleware (threading locks, etc.)
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def dumps_typed(self, obj: Any) -> Tuple[str, bytes]:
        """
        Serialize object, handling unpicklable middleware objects gracefully.
        """
        try:
            # Try the parent class method first (handles msgpack, json, pickle)
            return super().dumps_typed(obj)
        except (TypeError, AttributeError, pickle.PicklingError) as e:
            # If pickle fails due to threading locks or other unpicklable objects,
            # try to create a simplified representation
            if "cannot pickle '_thread.lock'" in str(e) or "cannot pickle" in str(e):
                logger.warning(f"Object {type(obj)} contains unpicklable elements, using simplified representation")
                
                # Create a simplified version of the object
                try:
                    # For complex objects, try to extract just the essential data
                    if hasattr(obj, '__dict__'):
                        # Create a dict of picklable attributes
                        simple_obj = {}
                        for key, value in obj.__dict__.items():
                            try:
                                # Test if this attribute is picklable
                                pickle.dumps(value)
                                simple_obj[key] = value
                            except:
                                # Skip unpicklable attributes
                                simple_obj[key] = f"<unpicklable: {type(value).__name__}>"
                        
                        # Add type information
                        simple_obj['__type__'] = type(obj).__name__
                        return "pickle", pickle.dumps(simple_obj)
                    else:
                        # For objects without __dict__, use string representation
                        return "json", str(obj).encode('utf-8')
                except Exception as inner_e:
                    logger.error(f"Failed to create simplified representation: {inner_e}")
                    # Last resort: use string representation
                    return "json", str(obj).encode('utf-8')
            else:
                # Re-raise if it's a different error
                raise
