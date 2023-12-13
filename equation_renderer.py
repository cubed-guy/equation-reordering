# TODO: Integrate reordering.py so that it looks nice

import pygame
pygame.font.init()  # hope this doesn't bite me later
c = type('c', (), {'__matmul__': (lambda s, x: (*x.to_bytes(3, 'big'),)), '__sub__': (lambda s, x: (x&255,)*3)})()

from abc import ABC, abstractmethod

class Expression(ABC):
	exp: None

	def __len__(self):
		return self.exp.__len__()  # don't use global len because it may be overriden

	def __init__(self, exp):
		self.exp = exp

	def __repr__(self):
		return f'{self.__class__.__name__}({self!s})'

	@abstractmethod
	def render(self): pass

	# @abstractmethod
	def cursor_line(self, cursor_path): pass

	@abstractmethod
	def cursor_prev(self, cursor_path): pass

	@abstractmethod
	def cursor_next(self, cursor_path): pass

	@abstractmethod
	def cursor_last(self): pass

	@abstractmethod
	def cursor_first(self): pass

	@abstractmethod  # subclasses must implement this method to be instantiable
	def __str__(self): pass

	def __getitem__(self, cursor_path):
		if not cursor_path: return self
		return self.exp[cursor_path[0]][cursor_path[1:]]

class StringExpression(Expression):
	exp: str

	def __str__(self):
		return self.exp

	def __init__(self, exp, font, col):
		super().__init__(exp)
		self.font = font
		self.col = col

	def render(self):
		print('render', self)

		tsurf = self.font.render(self.exp, True, self.col)
		out = pygame.Surface(
			(tsurf.get_width(), tsurf.get_height()), pygame.SRCALPHA
		)
		out.blit(tsurf, (0, 0))

		return out
	
	def cursor_rect(self, cursor_path):
		if len(cursor_path) != 1:
			raise TypeError('Raw expressions support only a single integer as path')

		cur_x, cur_h = self.font.size(self.exp[:cursor_path[0]])

		return (cur_x, cur_h // 10, self.cur_w, cur_h * 4 // 5)

	def cursor_prev(self, cursor_path):
		if len(cursor_path) != 1:
			raise TypeError('String expressions support only a single integer as path')

		cursor_idx = cursor_path[0]
		if cursor_idx <= 0: return None
		else:
			print('STRING PREV', cursor_idx, [len(cursor_path)])
			return [cursor_idx - 1]

	def cursor_next(self, cursor_path):
		if len(cursor_path) != 1:
			raise TypeError('String expressions support only a single integer as path')

		cursor_idx = cursor_path[0]
		if cursor_idx >= len(self.exp): return None  # represents out of bounds
		else:
			print('STRING NEXT', cursor_idx, [len(cursor_path)])
			return [cursor_idx + 1]

	def cursor_last(self):
		return [len(self.exp)]

	def cursor_first(self):
		return [0]

class CompoundExpression(Expression):  # vertically centered
	exp: list[Expression]

	def __str__(self):
		return ''.join(map(str, self.exp))

	def render(self):
		# print('render', repr(self), cursor_path)

		print(self)

		surfs = [sub_exp.render() for sub_exp in self.exp]

		w = sum(surf.get_width() for surf in surfs)
		h = max(surf.get_height() for surf in surfs)
		out = pygame.Surface((w, h), pygame.SRCALPHA)
		x = 0
		for surf, sub_exp in zip(surfs, self.exp):
			print(sub_exp, 'at', x)
			out.blit(surf, (x, (h - surf.get_height())//2))
			x += surf.get_width()
		return out

	def cursor_rect(self, cursor_path):
		for i, sub_exp in enumerate(self.exp):
			if i == cursor_path[0]:
				sub_path = cursor_path[1:]
			else:
				sub_path = None

	def cursor_prev(self, cursor_path):
		child_idx = cursor_path[0]
		if child_idx not in range(len(self.exp)):
			raise IndexError('Cursor path out of range')

		prev_path = self.exp[child_idx].cursor_prev(cursor_path[1:])

		if prev_path is not None: return [child_idx] + prev_path

		if child_idx <= 0: return None
		child_idx -= 1

		print('COMPOUND PREV', child_idx, [len(cursor_path)])

		return [child_idx] + self.exp[child_idx].cursor_last()

	def cursor_next(self, cursor_path):
		child_idx = cursor_path[0]
		next_path = self.exp[child_idx].cursor_next(cursor_path[1:])

		if next_path is not None: return [child_idx] + next_path

		print('COMPOUND NEXT', child_idx, [len(cursor_path)])

		child_idx += 1
		if child_idx >= len(self.exp): return None

		return [child_idx] + self.exp[child_idx].cursor_first()

	def cursor_last(self):
		if not self.exp: return []
		return [len(self.exp)-1] + self.exp[-1].cursor_last()

	def cursor_first(self):
		if not self.exp: return []
		return [0] + self.exp[0].cursor_first()

	def insert_after(self, cursor_path, exp):
		'''
		
		'''

class AlignedExpression(CompoundExpression):
	'''
	first_element = second_element
	              = third_element
	              = ...
	'''

	def __init__(self, exp, font, col):
		super().__init__(exp)
		self.font = font
		self.col = col

	def render(self):
		# print('render', repr(self), cursor_path)

		lhs_surf, *surfs = (sub_exp.render() for sub_exp in self.exp)
		eq_surf = self.font.render('=', True, self.col)

		x = max(surf.get_width() for surf in surfs) + eq_surf.get_width()
		w = x + lhs_surf.get_width()

		h = sum(surf.get_height() for surf in surfs)
		top_row_height = max(lhs_surf.get_height(), surfs[0].get_height())
		y = top_row_height - surfs[0].get_height()
		h += y

		out = pygame.Surface((w, h), pygame.SRCALPHA)
		for surf in surfs:
			out.blit(surf, (x, (h - surf.get_height())//2))
			x += surf.get_width()
		return out


class FractionExpression(CompoundExpression):
	exp: tuple[Expression, Expression]

	def __str__(self):
		return f'{self.num}/{self.den}'

	def __init__(self, exp, col):
		super().__init__(exp)
		self.col = col
		self.num = exp[0]
		self.den = exp[1]

	def render(self):
		# print('render', repr(self), cursor_path)

		# if cursor_path is None:
		# 	print('no cursor path')
		# 	num_cursor_path = None
		# 	den_cursor_path = None
		# elif cursor_path[0] == 0:
		# 	print('cursor path goes into num')
		# 	num_cursor_path = cursor_path[1:]
		# 	den_cursor_path = None
		# else:
		# 	print('cursor path goes into den')
		# 	num_cursor_path = None
		# 	den_cursor_path = cursor_path[1:]

		num_surf = self.num.render()
		den_surf = self.den.render()
		w = max(num_surf.get_width(), den_surf.get_width())
		num_height = num_surf.get_height()
		h = num_height + den_surf.get_height()

		out = pygame.Surface((w, h), pygame.SRCALPHA)
		# print(num_surf, den_surf, w, h)

		out.blit(num_surf, ((w - num_surf.get_width())//2, 0))
		out.fill(self.col, (0, num_height, w, 4))
		out.blit(den_surf, ((w - den_surf.get_width())//2, num_height))
		return out

class ContainerExpression(Expression):
	def __getitem__(self, cursor_path):
		print('accessing', cursor_path, 'for container exp')
		return self.exp[cursor_path]

	def cursor_prev(self, cursor_path):
		return self.exp.cursor_prev(cursor_path)

	def cursor_next(self, cursor_path):
		return self.exp.cursor_next(cursor_path)

	def cursor_first(self):
		return self.exp.cursor_first()

	def cursor_last(self):
		return self.exp.cursor_last()

class SubscriptExpression(ContainerExpression):
	# offset is from the center
	exp: Expression

	def __str__(self):
		return f'^({self.exp})'

	def __init__(self, exp, offset):
		super().__init__(exp)
		self.offset = offset

	def render(self):
		print('render', self.exp)

		surf = self.exp.render()

		w = surf.get_width()
		h = surf.get_height() + 2 * abs(self.offset)
		out = pygame.Surface((w, h), pygame.SRCALPHA)

		out.blit(surf, (0, (h - surf.get_height())//2 - self.offset))

		return out

class BracketExpression(ContainerExpression):
	def __init__(self, exp, brackets, font_path, colour):
		super().__init__(exp)
		self.font_path = font_path
		self.brackets = brackets
		self.colour = colour

	def render(self):
		surf = self.exp.render()

		h = surf.get_height()

		font = pygame.font.Font(self.font_path, True, h * 4 // 5)

		bracket_l = font.render(self.brackets[0], True, self.colour)
		bracket_r = font.render(self.brackets[1], True, self.colour)

		surf_x = bracket_l.get_width()
		bracket_r_x = surf_x + surf.get_width()
		w = bracket_r_x + bracket_r.get_width()
		h = max(h, bracket_l.get_height(), bracket_r.get_height())

		out = pygame.Surface((w, h), pygame.SRCALPHA)

		y = (h - bracket_l.get_height()) // 2
		out.blit(bracket_l, (0, y))

		y = (h - surf.get_height()) // 2
		out.blit(surf, (surf_x, y))

		y = (h - bracket_r.get_height()) // 2
		out.blit(bracket_r, (bracket_r_x, y))

		return out


class Stack_object:
	font_path = '../Product Sans Regular.ttf'
	font_size = 24
	font = pygame.font.Font(font_path, font_size)
	colour = c@0xff9088

	@classmethod  # only for recursion
	def get_renderer(cls, exp, colour=colour, size=font_size):
		if size != cls.font_size:
			print(exp, 'at size', size)
			font = pygame.font.Font(cls.font_path, size)
		else:
			font = cls.font

		if isinstance(exp, reordering.Sum):
			if not exp.exps: return StringExpression('0', font, colour)

			renderers = [cls.get_renderer(exp.exps[0])]
			for sub_exp in exp.exps[1:]:
				if isinstance(sub_exp, reordering.Neg):
					renderers.append(StringExpression('-', font, colour))
					sub_exp = sub_exp.exp
				else:
					renderers.append(StringExpression('+', font, colour))

				renderer = cls.get_renderer(sub_exp)
				if isinstance(sub_exp, reordering.Sum):
					renderer = BracketExpression(
						renderer, '()', cls.font_path, cls.colour
					)

				renderers.append(renderer)

			return CompoundExpression(renderers)

		if isinstance(exp, reordering.Product):
			if not exp.exps: return StringExpression('1', font, colour)

			renderers = [cls.get_renderer(exp.exps[0])]
			for sub_exp in exp.exps[1:]:
				if isinstance(sub_exp, reordering.Inv):
					# create a frac type
					renderers.append(StringExpression('/', font, colour))
					sub_exp = sub_exp.exp

				renderer = cls.get_renderer(sub_exp)
				if isinstance(
					sub_exp, (reordering.Sum, reordering.Product)
				):
					renderer = BracketExpression(
						renderer, '()', cls.font_path, cls.colour
					)

				renderers.append(renderer)

			return CompoundExpression(renderers)

		if isinstance(exp, reordering.Neg):
			minus = StringExpression('-', font, colour)
			renderer = cls.get_renderer(exp.exp)
			if isinstance(exp.exp, reordering.Sum):
				renderer = BracketExpression(
					renderer, '()', cls.font_path, cls.colour
				)

			return CompoundExpression([minus, renderer])

		if isinstance(exp, reordering.Inv):
			sub_font = pygame.font.Font(cls.font_path, size*4//5)
			inv = StringExpression('-1', sub_font, cls.colour)
			inv = SubscriptExpression(inv, -size // 2)

			renderer = cls.get_renderer(exp.exp)
			if isinstance(
				exp.exp,
				(reordering.Sum, reordering.Neg, reordering.Product),
			):
				renderer = BracketExpression(
					renderer, '()', cls.font_path, cls.colour
				)

			return CompoundExpression([renderer, inv])

		if isinstance(exp, reordering.Exp):
			print('exp is', exp.exp)
			exponent = cls.get_renderer(exp.exp, size=size * 4 // 5)
			exponent = SubscriptExpression(exponent, size // 2)

			print('base is', exp.base)
			print('Full power expression is', exp)
			base = cls.get_renderer(exp.base)
			if isinstance(
				exp.exp,
				(reordering.Sum, reordering.Neg, reordering.Product),
			):
				base = BracketExpression(
					base, '()', cls.font_path, cls.colour
				)

			return CompoundExpression([base, exponent])

		if isinstance(exp, reordering.Fn):
			fn = StringExpression(exp.name)
			arg = BracketExpression(
				cls.get_renderer(exp.arg), '()', cls.font_path, cls.colour
			)
			return CompoundExpression([fn, arg])

		if isinstance(exp, reordering.Const):
			return StringExpression(f'{exp.value}', font, cls.colour)

		if isinstance(exp, reordering.Var):
			return StringExpression(f'{exp.name}', font, cls.colour)

		raise TypeError(f'{type(exp).__name__} is not yet implemented')

	def __init__(self, exp, size):
		self.exp = exp
		self.renderer = self.get_renderer(exp)
		self.cache_surf = None

	def render(self):
		return self.renderer.render()

class Command_processor:
	from reordering import Const, Var, Sum, Product, Neg, Exp, Fn

	size = 25

	def __init__(self):
		self.stack = [Stack_object(self.Const(0), self.size)]

	def append(self, exp):
		self.stack.append(Stack_object(exp, self.size))

	def insert(self, idx, exp):
		self.stack.insert(idx, Stack_object(exp, self.size))

	def extend(self, iterable):
		self.stack.extend((Stack_object(exp, self.size) for exp in iterable))

	def pop(self, idx=-1, /):
		obj = self.stack.pop(idx)
		return obj.exp
	
	def submit_command(self, command):
		out = StringIO()

		try:
			if   command == '+': r = self.pop(); self.append(self.pop() + r)
			elif command == '-': r = self.pop(); self.append(self.pop() - r)
			elif command == '*': r = self.pop(); self.append(self.pop() * r)
			elif command == '/': r = self.pop(); self.append(self.pop() / r)
			elif command == '^': r = self.pop(); self.append(self.pop() ** r)

			elif command == '_': self.append(-self.pop())
			elif command == '.': self.append(self.pop().simplify())
			elif command.startswith('.'):
				split = command[1:].split()

				if len(split) == 2:  # select index
					print('select', file=out)
					index, name = split
					index = int(index)
					self.extend(self.pop().select(name, index)[::-1])

				elif len(split) == 3:  # select slice
					print('select slice', file=out)
					start, stop, name = split
					start = int(start)
					stop = int(stop)
					self.extend(self.pop().select(name, slice(start, stop))[::-1])
				else:
					raise ValueError('Invalid Command Format. Expected exactly 2 or 3 arguments')

			elif command == ',': self.append(self.pop().distribute().simplify())
			elif command.startswith(','):
				exp = self.pop()
				if isinstance(exp, self.Neg):
					neg = True
					exp = exp.exp
				else:
					neg = False

				if not isinstance(exp, self.Sum): raise TypeError('Can only factorise Sum types')
				term = exp.e[0]

				if isinstance(term, Neg): term = term.exp

				index = int(command[1:])

				if isinstance(term, self.Product):
					fac_exp = term.exps[index]
				elif index != 0:
					raise IndexError('Prime term can only be indexed with 0')
				else:
					fac_exp = term

				if neg:
					self.append((-exp.factor(fac_exp)).simplify())
				else:
					self.append(exp.factor(fac_exp).simplify())

			elif command == '$': self.append(self.stack[-1].exp)
			elif command.startswith('$'): self.append(self.stack[-int(command[1:])].exp)

			elif command.startswith('!'):
				self.append(self.Fn(*command[1:].split(), self.pop()))

			elif command == '\\':
				self.pop()

			elif command.startswith('/s'):
				split = command[2:].split()
				if len(split) == 0:  # swap
					print('swap', file=out)
					self.append(self.pop(-2))
				elif len(split) == 1:  # substitute
					print('sub', file=out)
					name = split[0]
					sub_exp = self.pop()
					exp = self.pop()
					self.extend([exp.substitute(self.Var(name), sub_exp), sub_exp])
				else:
					raise ValueError('Invalid Command Format. Expected at most 1 argument')

			elif command == '=':
				self.append(self.pop().eval_consts())

			elif command.startswith('=='):
				name = command[2:]
				self.append(self.pop().solve_for(self.Var(name), rhs=self.pop()))

			elif command.startswith('='):
				index = command[1:]
				if ' ' not in index: index = int(index)
				else:
					start, stop = index.split()
					# prin, file=outt(start, stop)
					index = slice(int(start), int(stop))

				print(index, file=out)

				self.extend((self.pop().extract(self.pop(), index))[::-1])

			else:
				self.append(self.Var(command))

		except Exception as e:
			print(f'Could not execute ({e.__class__.__name__})', file=out)
			print(e, file=out)
			# raise e
		
		if not self.stack or self.stack[0].exp != self.Const(0):
			self.insert(0, self.Const(0))

		return out.getvalue()

if __name__ == '__main__':
	from io import StringIO
	import reordering
	from pygame.locals import *

	pygame.font.init()
	font  = pygame.font.Font('../Product Sans Regular.ttf', 32)
	efont = pygame.font.Font('../Product Sans Regular.ttf', 24)
	sfont = pygame.font.Font('../Product Sans Regular.ttf', 12)


	bg = c-34
	fg = c@0xff9088
	green = c@0xa0ffe0

	fps = 60

	w, h = res = (1280, 720)
	sh = 20

	class Chain(Stack_object):
		def __init__(
			self, lhs: reordering.Expression, rhs: reordering.Expression
		):
			self.lhs = lhs
			self.rhs = [rhs]

		def append(self, exp):
			self.rhs.append(exp)

		def undo(self):
			self.rhs.pop()

		def flip(self):
			return Chain(rhs[-1], lhs)

	def updateStat(msg = None, update = True):
		rect = (0, h-sh, w, 21)
		display.fill(c-0, rect)

		tsurf = sfont.render(msg or f'{cmd!r} {command_processor.stack}', True, c--1)
		display.blit(tsurf, (5, h-sh))

		if update: pygame.display.update(rect)

	def resize(size):
		global w, h, res, display
		w, h = res = size
		display = pygame.display.set_mode(res, RESIZABLE)
		updateDisplay()

	def updateDisplay():
		display.fill(bg)

		for exp in command_processor.stack:
			if exp.cache_surf is None:
				exp.cache_surf = exp.render()

		surf_stack = [exp.cache_surf for exp in command_processor.stack]

		offset = h-sh-sum(surf.get_height() for surf in surf_stack)

		for surf in surf_stack:
			x = (w - surf.get_width()) // 2
			display.blit(surf, (x, offset))
			offset += surf.get_height()

		updateStat(update = False)
		pygame.display.flip()

	def toggleFullscreen():
		global pres, res, w, h, display
		res, pres =  pres, res
		w, h = res
		if display.get_flags()&FULLSCREEN: resize(res)
		else: display = pygame.display.set_mode(res, FULLSCREEN); updateDisplay()

	pos = [0, 0]
	dragging = False

	curr_exp = CompoundExpression(
		(
			# Expression('1 + ', font, fg),
			# FractionExpression((
			# 	Expression('1', font, fg),
			# 	Expression('22', font, fg),
			# ), font, fg),
			StringExpression('0.34', font, fg),
			SubscriptExpression(
				StringExpression('5', efont, fg), 15
			),
		))

	# cursor_path = [1, 0]

	surf_cache = None

	cmd = ''

	command_processor = Command_processor()

	# print(cursor_path)

	resize(res)
	pres = pygame.display.list_modes()[0]
	clock = pygame.time.Clock()
	running = True
	while running:
		for event in pygame.event.get():
			if event.type == KEYDOWN:
				if   event.key == K_ESCAPE: running = False
				elif event.key == K_F11: toggleFullscreen()
				
				elif event.key == K_RETURN:
					output = command_processor.submit_command(cmd)
					print(output, end='')
					cmd = ''

				elif event.mod & (KMOD_LCTRL|KMOD_RCTRL):
					if event.key == K_BACKSPACE:
						split = cmd.rsplit(maxsplit=1)
						if len(split) <= 1: cmd = ''
						else: cmd = split[0]
				elif event.key == K_BACKSPACE:
					cmd = cmd[:-1]
				elif event.unicode and event.unicode.isprintable():
					cmd += event.unicode

			elif event.type == VIDEORESIZE:
				if not display.get_flags()&FULLSCREEN: resize(event.size)
			elif event.type == QUIT: running = False
			elif event.type == MOUSEBUTTONDOWN:
				if event.button in (4, 5):
					delta = event.button*2-9
				elif event.button == 1:
					dragging = True
			elif event.type == MOUSEBUTTONUP:
				if event.button == 1:
					dragging = False
			elif event.type == MOUSEMOTION:
				if dragging:
					pos[0] += event.rel[0]
					pos[1] += event.rel[1]

		updateDisplay()
		clock.tick(fps)
