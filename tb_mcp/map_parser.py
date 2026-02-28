"""
Quake .map format parser
Ported from TrenchBroom's MapReader.cpp
Recursive descent parser supporting standard Quake map format
"""
from typing import Optional, Tuple, List
from .map_types import Vec3, Face, Brush, Entity, MapFile


class ParseError(Exception):
    """Parser error with line/column info"""
    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"{message} at line {line}, column {column}")
        self.line = line
        self.column = column


class MapParser:
    """Recursive descent parser for Quake .map format"""
    
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.length = len(source)
    
    def parse(self) -> MapFile:
        """Parse entire map file and return MapFile"""
        mapfile = MapFile()
        
        self._skip_whitespace_and_comments()
        
        while self.pos < self.length:
            self._skip_whitespace_and_comments()
            
            if self.pos >= self.length:
                break
            
            if self._peek() == '{':
                entity = self._parse_entity()
                mapfile.add_entity(entity)
            else:
                raise ParseError(
                    f"Expected '{{' to start entity, got '{self._peek()}'",
                    self.line, self.column
                )
            
            self._skip_whitespace_and_comments()
        
        return mapfile
    
    def _parse_entity(self) -> Entity:
        """Parse entity: { properties brushes }"""
        self._expect('{')
        self._skip_whitespace_and_comments()
        
        entity = Entity()
        
        # Parse properties first
        while self.pos < self.length and self._peek() == '"':
            key, value = self._parse_property()
            entity.set_property(key, value)
            self._skip_whitespace_and_comments()
        
        # Then parse brushes
        while self.pos < self.length and self._peek() == '{':
            brush = self._parse_brush()
            entity.brushes.append(brush)
            self._skip_whitespace_and_comments()
        
        self._expect('}')
        
        return entity
    
    def _parse_property(self) -> Tuple[str, str]:
        """Parse property: key value pair in quotes"""
        key = self._parse_quoted_string()
        self._skip_whitespace_and_comments()
        value = self._parse_quoted_string()
        return (key, value)
    
    def _parse_brush(self) -> Brush:
        """Parse brush: { faces }"""
        self._expect('{')
        self._skip_whitespace_and_comments()
        
        brush = Brush()
        
        # Parse faces until we hit closing brace
        while self.pos < self.length and self._peek() == '(':
            face = self._parse_face()
            brush.faces.append(face)
            self._skip_whitespace_and_comments()
        
        self._expect('}')
        
        return brush
    
    def _parse_face(self) -> Face:
        """Parse face: ( p1 ) ( p2 ) ( p3 ) texture u v rot su sv"""
        # Parse three points
        point1 = self._parse_point()
        self._skip_whitespace()
        
        point2 = self._parse_point()
        self._skip_whitespace()
        
        point3 = self._parse_point()
        self._skip_whitespace()
        
        # Parse texture name
        texture = self._parse_token()
        self._skip_whitespace()
        
        # Parse texture parameters
        try:
            offset_u = float(self._parse_token())
            self._skip_whitespace()
            
            offset_v = float(self._parse_token())
            self._skip_whitespace()
            
            rotation = float(self._parse_token())
            self._skip_whitespace()
            
            scale_u = float(self._parse_token())
            self._skip_whitespace()
            
            scale_v = float(self._parse_token())
        except ValueError as e:
            raise ParseError(
                f"Invalid numeric value in face: {e}",
                self.line, self.column
            )
        
        return Face(
            point1=point1,
            point2=point2,
            point3=point3,
            texture=texture,
            offset_u=offset_u,
            offset_v=offset_v,
            rotation=rotation,
            scale_u=scale_u,
            scale_v=scale_v
        )
    
    def _parse_point(self) -> Vec3:
        """Parse point: ( x y z )"""
        self._expect('(')
        self._skip_whitespace()
        
        try:
            x = float(self._parse_token())
            self._skip_whitespace()
            
            y = float(self._parse_token())
            self._skip_whitespace()
            
            z = float(self._parse_token())
        except ValueError as e:
            raise ParseError(
                f"Invalid coordinate in point: {e}",
                self.line, self.column
            )
        
        self._skip_whitespace()
        self._expect(')')
        
        return Vec3(x, y, z)
    
    def _parse_quoted_string(self) -> str:
        """Parse a quoted string: \"content\""""
        self._expect('"')
        
        start = self.pos
        while self.pos < self.length and self._peek() != '"':
            self._advance()
        
        content = self.source[start:self.pos]
        self._expect('"')
        
        return content
    
    def _parse_token(self) -> str:
        """Parse a non-whitespace token"""
        self._skip_whitespace()
        
        start = self.pos
        
        # Handle quoted strings as tokens
        if self._peek() == '"':
            return self._parse_quoted_string()
        
        # Read until whitespace or special characters
        while self.pos < self.length:
            c = self._peek()
            if c.isspace() or c in '{}()':
                break
            self._advance()
        
        if start == self.pos:
            raise ParseError(
                f"Expected token, got '{self._peek()}'",
                self.line, self.column
            )
        
        return self.source[start:self.pos]
    
    def _skip_whitespace(self) -> None:
        """Skip whitespace but not newlines"""
        while self.pos < self.length and self._peek() in ' \t\r':
            self._advance()
    
    def _skip_whitespace_and_comments(self) -> None:
        """Skip whitespace and // style comments"""
        while self.pos < self.length:
            c = self._peek()
            
            # Single-line comments
            if c == '/' and self.pos + 1 < self.length and self.source[self.pos + 1] == '/':
                self._advance()  # skip first /
                self._advance()  # skip second /
                # Skip until newline
                while self.pos < self.length and self._peek() not in '\n\r':
                    self._advance()
            
            # Whitespace
            elif c.isspace():
                self._advance()
            
            # Not whitespace or comment, done
            else:
                break
    
    def _peek(self) -> str:
        """Peek at current character"""
        if self.pos < self.length:
            return self.source[self.pos]
        return '\0'
    
    def _advance(self) -> str:
        """Advance to next character, updating line/column"""
        if self.pos >= self.length:
            return '\0'
        
        c = self.source[self.pos]
        self.pos += 1
        
        if c == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        
        return c
    
    def _expect(self, expected: str) -> None:
        """Expect a specific character"""
        actual = self._peek()
        if actual != expected:
            raise ParseError(
                f"Expected '{expected}', got '{actual}'",
                self.line, self.column
            )
        self._advance()


def parse_map(source: str) -> MapFile:
    """Parse map from string source"""
    parser = MapParser(source)
    return parser.parse()


def parse_map_file(filepath: str) -> MapFile:
    """Parse map from file"""
    with open(filepath, 'r') as f:
        source = f.read()
    return parse_map(source)
