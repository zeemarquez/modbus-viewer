"""
Variable expression evaluator for computing values from registers.
"""

import ast
import math
import operator
import re
from typing import Dict, List, Optional, Callable, Union

from src.models.variable import Variable
from src.models.register import Register


class VariableEvaluator:
    """
    Evaluates variable expressions using register values.
    
    Supports:
    - Register references: R0, R1, R100 (uses scaled register value)
    - Operators: +, -, *, /, //, %, **
    - Functions: abs, min, max, sqrt, round, sin, cos, tan
    - Parentheses for grouping
    - Numbers (int and float)
    
    Example expressions:
    - "R0 + R1"
    - "R0 * 0.5 + R1 * 0.5"
    - "sqrt(R0**2 + R1**2)"
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
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'log': math.log,
        'log10': math.log10,
        'exp': math.exp,
    }
    
    def __init__(self):
        self._registers: List[Register] = []
        self._register_map: Dict[int, Register] = {}  # address -> register
    
    def set_registers(self, registers: List[Register]) -> None:
        """Set the available registers for expression evaluation."""
        self._registers = registers
        self._register_map = {r.address: r for r in registers}
    
    def _preprocess_expression(self, expression: str) -> str:
        """
        Preprocess expression to convert register references to variable names.
        
        Converts:
        - R0, R1, R100 -> _R0, _R1, _R100
        """
        # Replace R<address> references
        reg_pattern = r'\bR(\d+)\b'
        result = re.sub(reg_pattern, r'_R\1', expression)
        return result
    
    def _get_variables(self, expression: str) -> Dict[str, float]:
        """Get variable values for the expression."""
        variables = {}
        
        # Find R<address> references
        reg_pattern = r'\bR(\d+)\b'
        for match in re.finditer(reg_pattern, expression):
            address = int(match.group(1))
            var_name = f"_R{address}"
            if address in self._register_map:
                reg = self._register_map[address]
                if reg.scaled_value is not None:
                    variables[var_name] = reg.scaled_value
                else:
                    variables[var_name] = 0.0
            else:
                variables[var_name] = 0.0
        
        return variables
    
    def evaluate(self, expression: str) -> float:
        """
        Evaluate an expression using current register values.
        
        Args:
            expression: Expression string with register references
            
        Returns:
            Calculated result
            
        Raises:
            ValueError: If expression is invalid or division by zero occurs
        """
        if not expression or not expression.strip():
            return 0.0
        
        # Get variable values
        variables = self._get_variables(expression)
        
        # Preprocess expression
        processed = self._preprocess_expression(expression)
        
        # Parse and evaluate
        try:
            tree = ast.parse(processed, mode='eval')
            return self._eval_node(tree.body, variables)
        except SyntaxError as e:
            raise ValueError(f"Invalid expression syntax: {e}")
        except ZeroDivisionError:
            raise ValueError("Division by zero")
        except Exception as e:
            raise ValueError(f"Expression evaluation failed: {e}")
    
    def _eval_node(self, node: ast.AST, variables: dict) -> Union[int, float]:
        """Recursively evaluate an AST node."""
        
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return float(node.value)
            raise ValueError(f"Unsupported constant type: {type(node.value)}")
        
        elif isinstance(node, ast.Name):
            if node.id in variables:
                return variables[node.id]
            raise ValueError(f"Unknown variable: {node.id}")
        
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left, variables)
            right = self._eval_node(node.right, variables)
            op_func = self.OPERATORS.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            
            # Check for division by zero
            if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                if abs(right) < 1e-10:  # Very small threshold for floating point
                    raise ZeroDivisionError("Division by zero")
            
            try:
                return op_func(left, right)
            except ZeroDivisionError:
                raise ValueError("Division by zero")
        
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand, variables)
            op_func = self.OPERATORS.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
            return op_func(operand)
        
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only simple function calls are allowed")
            
            func_name = node.func.id
            if func_name not in self.FUNCTIONS:
                raise ValueError(f"Unknown function: {func_name}")
            
            args = [self._eval_node(arg, variables) for arg in node.args]
            
            # Check for invalid function arguments
            if func_name in ('sqrt', 'log', 'log10') and args[0] < 0:
                raise ValueError(f"{func_name}() argument must be non-negative")
            
            try:
                return self.FUNCTIONS[func_name](*args)
            except (ValueError, ZeroDivisionError) as e:
                raise ValueError(f"Function {func_name}() error: {e}")
        
        elif isinstance(node, ast.IfExp):
            condition = self._eval_node(node.test, variables)
            if condition:
                return self._eval_node(node.body, variables)
            else:
                return self._eval_node(node.orelse, variables)
        
        else:
            raise ValueError(f"Unsupported expression type: {type(node).__name__}")
    
    def validate(self, expression: str) -> Optional[str]:
        """
        Validate an expression.
        
        Returns:
            None if valid, error message if invalid
        """
        if not expression or not expression.strip():
            return "Expression is empty"
        
        try:
            processed = self._preprocess_expression(expression)
            tree = ast.parse(processed, mode='eval')
            
            # Create dummy variables for validation
            variables = {}
            reg_pattern = r'_R(\d+)'
            for match in re.finditer(reg_pattern, processed):
                variables[match.group(0)] = 1.0  # Use 1.0 instead of 0 to avoid division by zero in validation
            
            self._eval_node(tree.body, variables)
            return None
        except Exception as e:
            return str(e)
    
    def get_referenced_registers(self, expression: str) -> List[int]:
        """Get list of register addresses referenced in expression."""
        addresses = []
        
        # Find R<address> references
        reg_pattern = r'\bR(\d+)\b'
        for match in re.finditer(reg_pattern, expression):
            address = int(match.group(1))
            if address not in addresses:
                addresses.append(address)
        
        return addresses
