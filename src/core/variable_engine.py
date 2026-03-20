"""
Variable expression evaluator for computing values from registers.
Supports multi-device register references with D<id>.R<addr> syntax.
"""

import ast
import math
import operator
import re
from typing import Dict, List, Optional, Callable, Union, Tuple

from src.models.variable import Variable
from src.models.register import Register


class VariableEvaluator:
    """
    Evaluates variable expressions using register values.
    
    Supports:
    - Register references: D1.R0, D1.R100, D2.R0 (device.register syntax)
    - Legacy register references: R0, R1 (defaults to device 1)
    - Operators: +, -, *, /, //, %, **
    - Functions: abs, min, max, sqrt, round, sin, cos, tan
    - Parentheses for grouping
    - Numbers (int and float)
    
    Example expressions:
    - "D1.R0 + D1.R1"
    - "D1.R0 * 0.5 + D2.R0 * 0.5"
    - "sqrt(D1.R0**2 + D1.R1**2)"
    - "R0 + R1"  (legacy, defaults to D1)
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
        # Buffering functions (implemented via history in _eval_node).
        # These are still included so the UI can discover them.
        'avg': lambda _x, _n: float("nan"),
        'std': lambda _x, _n: float("nan"),
    }
    
    def __init__(self):
        self._registers: List[Register] = []
        self._register_map: Dict[Tuple[int, int], Register] = {}  # (slave_id, address) -> register
        # Optional history resolver for buffering functions.
        # Signature: (history_key: str, limit: int) -> List[float]
        self._history_getter: Optional[Callable[[str, int], List[float]]] = None

    def set_history_getter(self, getter: Optional[Callable[[str, int], List[float]]]) -> None:
        """Set a history resolver for buffering functions (AVG/STD)."""
        self._history_getter = getter
    
    def set_registers(self, registers: List[Register]) -> None:
        """Set the available registers for expression evaluation."""
        self._registers = registers
        self._register_map = {(r.slave_id, r.address): r for r in registers}
    
    def _preprocess_expression(self, expression: str) -> str:
        """
        Preprocess expression to convert register references to variable names.
        
        Converts:
        - D1.R0, D1.R100 -> _D1_R0, _D1_R100
        - R0, R100 (legacy) -> _D1_R0, _D1_R100
        """
        # First, replace D<id>.R<addr> references
        full_pattern = r'\bD(\d+)\.R(\d+)\b'
        result = re.sub(full_pattern, r'_D\1_R\2', expression)
        
        # Then, replace legacy R<addr> references (not already prefixed with D)
        # Match R<addr> that is NOT preceded by _D<digits>_ (already converted)
        legacy_pattern = r'(?<!_D\d_)(?<!_D\d\d_)(?<!_D\d\d\d_)\bR(\d+)\b'
        result = re.sub(legacy_pattern, r'_D1_R\1', result)
        
        return result
    
    def _get_variables(self, expression: str) -> Dict[str, float]:
        """Get variable values for the expression."""
        variables = {}
        
        # Find D<id>.R<addr> references
        full_pattern = r'\bD(\d+)\.R(\d+)\b'
        for match in re.finditer(full_pattern, expression):
            slave_id = int(match.group(1))
            address = int(match.group(2))
            var_name = f"_D{slave_id}_R{address}"
            if (slave_id, address) in self._register_map:
                reg = self._register_map[(slave_id, address)]
                if reg.scaled_value is not None:
                    variables[var_name] = reg.scaled_value
                else:
                    variables[var_name] = 0.0
            else:
                variables[var_name] = 0.0
        
        # Find legacy R<addr> references (default to slave_id=1)
        legacy_pattern = r'(?<!\.)(?<!D\d)\bR(\d+)\b'
        for match in re.finditer(legacy_pattern, expression):
            address = int(match.group(1))
            var_name = f"_D1_R{address}"
            if var_name not in variables:
                if (1, address) in self._register_map:
                    reg = self._register_map[(1, address)]
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
            func_key = func_name.lower()

            # Buffered functions backed by DataEngine history:
            #   AVG(register_ref, samples)
            #   STD(register_ref, samples)  (aliases: STDEV/STDDEV)
            if func_key in ("avg", "average", "std", "stdev", "stddev"):
                return self._eval_buffered_stat_call(node, func_key, variables)

            if func_key not in self.FUNCTIONS:
                raise ValueError(f"Unknown function: {func_name}")
            
            args = [self._eval_node(arg, variables) for arg in node.args]
            
            # Check for invalid function arguments
            if func_key in ('sqrt', 'log', 'log10') and args[0] < 0:
                raise ValueError(f"{func_key}() argument must be non-negative")
            
            try:
                return self.FUNCTIONS[func_key](*args)
            except (ValueError, ZeroDivisionError) as e:
                raise ValueError(f"Function {func_key}() error: {e}")
        
        elif isinstance(node, ast.IfExp):
            condition = self._eval_node(node.test, variables)
            if condition:
                return self._eval_node(node.body, variables)
            else:
                return self._eval_node(node.orelse, variables)
        
        else:
            raise ValueError(f"Unsupported expression type: {type(node).__name__}")

    def _eval_buffered_stat_call(
        self,
        node: ast.Call,
        func_key: str,
        variables: dict,
    ) -> float:
        """Evaluate AVG/STD using a register history buffer.

        Signature:
          - AVG(register_ref, samples)
          - STD(register_ref, samples)  (aliases: STDEV/STDDEV)
        """
        if len(node.args) != 2:
            raise ValueError(f"{func_key.upper()} requires (register_ref, samples)")

        register_arg, samples_arg = node.args

        if not isinstance(register_arg, ast.Name):
            raise ValueError(f"{func_key.upper()} first argument must be a register reference")

        # Register placeholders look like: _D<sid>_R<addr>
        reg_placeholder = register_arg.id
        m = re.match(r"^_D(\d+)_R(\d+)$", reg_placeholder)
        if not m:
            raise ValueError(f"{func_key.upper()} register reference not recognized: {reg_placeholder}")

        slave_id = int(m.group(1))
        address = int(m.group(2))
        history_key = f"D{slave_id}.R{address}"

        if not isinstance(samples_arg, ast.Constant) or not isinstance(samples_arg.value, (int, float)):
            raise ValueError(f"{func_key.upper()} samples must be a number literal")

        samples = int(samples_arg.value)
        if samples <= 0:
            raise ValueError(f"{func_key.upper()} samples must be > 0")

        # If history is not available (editor preview / validate), return a safe default.
        if not self._history_getter:
            return 0.0

        values = self._history_getter(history_key, samples) or []
        if not values:
            return 0.0

        mean = sum(values) / len(values)

        if func_key in ("avg", "average"):
            return mean

        # Population standard deviation (ddof=0)
        var = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(var)
    
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
            # Match both D<id>.R<addr> and legacy R<addr> patterns in preprocessed form
            var_pattern = r'_D(\d+)_R(\d+)'
            for match in re.finditer(var_pattern, processed):
                variables[match.group(0)] = 1.0  # Use 1.0 instead of 0 to avoid division by zero in validation
            
            self._eval_node(tree.body, variables)
            return None
        except Exception as e:
            return str(e)
    
    def get_referenced_registers(self, expression: str) -> List[Tuple[int, int]]:
        """Get list of (slave_id, address) tuples referenced in expression."""
        refs = []
        
        # Find D<id>.R<addr> references
        full_pattern = r'\bD(\d+)\.R(\d+)\b'
        for match in re.finditer(full_pattern, expression):
            slave_id = int(match.group(1))
            address = int(match.group(2))
            ref = (slave_id, address)
            if ref not in refs:
                refs.append(ref)
        
        # Find legacy R<addr> references
        legacy_pattern = r'(?<!\.)(?<!D\d)\bR(\d+)\b'
        for match in re.finditer(legacy_pattern, expression):
            address = int(match.group(1))
            ref = (1, address)  # Default to device 1
            if ref not in refs:
                refs.append(ref)
        
        return refs
