"""
Safe expression evaluator for register scaling.
"""

import ast
import math
import operator
from typing import Union, Optional, Dict, Callable


class ExpressionEvaluator:
    """
    Safely evaluates mathematical expressions for register scaling.
    
    Supports:
    - Variable: value
    - Operators: +, -, *, /, //, %, **
    - Comparison: <, >, <=, >=, ==, !=
    - Functions: abs, min, max, sqrt, round, int, float
    - Parentheses for grouping
    - Numbers (int and float)
    
    Example expressions:
    - "value"
    - "value * 0.1"
    - "(value - 4000) / 16000 * 100"
    - "max(0, min(100, value))"
    """
    
    # Allowed operators
    OPERATORS: Dict[type, Callable] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
    }
    
    # Allowed functions
    FUNCTIONS: Dict[str, Callable] = {
        'abs': abs,
        'min': min,
        'max': max,
        'sqrt': math.sqrt,
        'round': round,
        'int': int,
        'float': float,
        'pow': pow,
    }
    
    def __init__(self):
        self._cache: Dict[str, ast.Expression] = {}
    
    def evaluate(
        self, 
        expression: str, 
        value: Union[int, float]
    ) -> Union[int, float]:
        """
        Evaluate expression with given value.
        
        Args:
            expression: Math expression string (use 'value' for the input)
            value: The raw register value
            
        Returns:
            Calculated result
            
        Raises:
            ValueError: If expression is invalid
            ZeroDivisionError: If division by zero occurs
        """
        if not expression or expression.strip() == "value":
            return value
        
        # Parse and cache the AST
        if expression not in self._cache:
            try:
                tree = ast.parse(expression, mode='eval')
                self._cache[expression] = tree
            except SyntaxError as e:
                raise ValueError(f"Invalid expression syntax: {e}")
        
        tree = self._cache[expression]
        
        # Evaluate with the value
        try:
            return self._eval_node(tree.body, {'value': value})
        except Exception as e:
            raise ValueError(f"Expression evaluation failed: {e}")
    
    def _eval_node(self, node: ast.AST, variables: dict) -> Union[int, float]:
        """Recursively evaluate an AST node."""
        
        if isinstance(node, ast.Constant):
            # Number literal
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant type: {type(node.value)}")
        
        elif isinstance(node, ast.Name):
            # Variable reference
            if node.id in variables:
                return variables[node.id]
            raise ValueError(f"Unknown variable: {node.id}")
        
        elif isinstance(node, ast.BinOp):
            # Binary operation (a + b, etc.)
            left = self._eval_node(node.left, variables)
            right = self._eval_node(node.right, variables)
            op_func = self.OPERATORS.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op_func(left, right)
        
        elif isinstance(node, ast.UnaryOp):
            # Unary operation (-a, +a)
            operand = self._eval_node(node.operand, variables)
            op_func = self.OPERATORS.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
            return op_func(operand)
        
        elif isinstance(node, ast.Compare):
            # Comparison (a < b)
            left = self._eval_node(node.left, variables)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, variables)
                op_func = self.OPERATORS.get(type(op))
                if op_func is None:
                    raise ValueError(f"Unsupported comparison: {type(op).__name__}")
                if not op_func(left, right):
                    return 0
                left = right
            return 1
        
        elif isinstance(node, ast.Call):
            # Function call
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only simple function calls are allowed")
            
            func_name = node.func.id
            if func_name not in self.FUNCTIONS:
                raise ValueError(f"Unknown function: {func_name}")
            
            args = [self._eval_node(arg, variables) for arg in node.args]
            return self.FUNCTIONS[func_name](*args)
        
        elif isinstance(node, ast.IfExp):
            # Ternary expression: a if condition else b
            condition = self._eval_node(node.test, variables)
            if condition:
                return self._eval_node(node.body, variables)
            else:
                return self._eval_node(node.orelse, variables)
        
        else:
            raise ValueError(f"Unsupported expression type: {type(node).__name__}")
    
    def validate(self, expression: str) -> Optional[str]:
        """
        Validate an expression without evaluating it.
        
        Args:
            expression: Expression to validate
            
        Returns:
            None if valid, error message if invalid
        """
        try:
            # Try to parse
            tree = ast.parse(expression, mode='eval')
            # Try to evaluate with a test value
            self._eval_node(tree.body, {'value': 0})
            return None
        except Exception as e:
            return str(e)
    
    def clear_cache(self) -> None:
        """Clear the expression cache."""
        self._cache.clear()


# Global instance for convenience
_evaluator = ExpressionEvaluator()


def evaluate_expression(
    expression: str, 
    value: Union[int, float]
) -> Union[int, float]:
    """Convenience function for evaluating expressions."""
    return _evaluator.evaluate(expression, value)


def validate_expression(expression: str) -> Optional[str]:
    """Convenience function for validating expressions."""
    return _evaluator.validate(expression)





