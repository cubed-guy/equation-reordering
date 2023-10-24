import pygame
from enum import Enum, auto

class Outer_move(Enum):
	prev = auto()
	curr = auto()
	next = auto()

class Expression:
	exp: str

	cur_w = 1
	cur_col = (192, 192, 192)

	def __len__(self):
		return self.exp.__len__()  # don't use global len because it may be overriden

	def __init__(self, exp, font, col):
		self.exp = exp
		self.font = font
		self.col = col

	def render(self, cursor_path):
		print('render', self, cursor_path)

		tsurf = self.font.render(self.exp, True, self.col)
		out = pygame.Surface((tsurf.get_width()+self.cur_w, tsurf.get_height()), SRCALPHA)
		out.blit(tsurf, (0, 0))

		if cursor_path is None:
			return out

		if len(cursor_path) != 1:
			raise TypeError('Raw expressions support only a single integer as path')

		cur_x, cur_h = self.font.size(self.exp[:cursor_path[0]])

		cur_w = 1
		out.fill(self.cur_col, (cur_x, cur_h // 10, self.cur_w, cur_h * 4 // 5))

		return out

	def cursor_prev(self, cursor_path):
		if len(cursor_path) != 1:
			raise TypeError('Raw expressions support only a single integer as path')

		cursor_idx = cursor_path[0]
		if cursor_idx <= 0: return None
		else:
			print('NORMAL PREV', cursor_idx, [len(cursor_path)])
			return [cursor_idx - 1]

	def cursor_next(self, cursor_path):
		if len(cursor_path) != 1:
			raise TypeError('Raw expressions support only a single integer as path')

		cursor_idx = cursor_path[0]
		if cursor_idx >= len(self.exp): return None  # represents out of bounds
		else:
			print('NORMAL NEXT', cursor_idx, [len(cursor_path)])
			return [cursor_idx + 1]

	def cursor_last(self):
		return [len(self.exp)]

	def cursor_first(self):
		return [0]

	def __getitem__(self, cursor_path):
		if not cursor_path: return self
		if len(cursor_path) == 1: return self.exp[cursor_path[0]]
		return self.exp[cursor_path[0]][cursor_path[1:]]

class CompoundExpression(Expression):  # vertically centered
	exp: list[Expression]

	def render(self, cursor_path):
		print('render', self, cursor_path)

		surfs = []
		for i, sub_exp in enumerate(self.exp):
			if i == cursor_path[0]:
				sub_path = cursor_path[1:]
			else:
				sub_path = None
			surfs.append(sub_exp.render(sub_path))

		w = sum(surf.get_width() for surf in surfs)
		h = max(surf.get_height() for surf in surfs)
		out = pygame.Surface((w, h), pygame.SRCALPHA)
		x = 0
		for surf in surfs:
			out.blit(surf, (x, (h - surf.get_height())//2))
			x += surf.get_width()
		return out

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
		prev_path = self.exp[child_idx].cursor_next(cursor_path[1:])

		if prev_path is not None: return [child_idx] + prev_path

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

class FractionExpression(CompoundExpression):
	exp: tuple[Expression, Expression]

	def __init__(self, exp, font, col):
		super().__init__(exp, font, col)
		self.num = exp[0]
		self.den = exp[1]

	def render(self, cursor_path):
		print('render', self, cursor_path)

		if cursor_path is None:
			print('no cursor path')
			num_cursor_path = None
			den_cursor_path = None
		elif cursor_path[0] == 0:
			print('cursor path goes into num')
			num_cursor_path = cursor_path[1:]
			den_cursor_path = None
		else:
			print('cursor path goes into den')
			num_cursor_path = None
			den_cursor_path = cursor_path[1:]

		num_surf = self.num.render(cursor_path=num_cursor_path)
		den_surf = self.den.render(cursor_path=den_cursor_path)
		w = max(num_surf.get_width(), den_surf.get_width())
		num_height = num_surf.get_height()
		h = num_height + den_surf.get_height()

		out = pygame.Surface((w, h), pygame.SRCALPHA)
		# print(num_surf, den_surf, w, h)

		out.blit(num_surf, ((w - num_surf.get_width())//2, 0))
		out.fill(self.col, (0, num_height, w, 4))
		out.blit(den_surf, ((w - den_surf.get_width())//2, num_height))
		return out


class SubscriptExpression(Expression):
	# offset is from the center
	exp: Expression

	def __init__(self, exp, font, col, offset):
		super().__init__(exp, font, col)
		self.offset = offset

	def render(self, cursor_path):
		print('render', self, cursor_path)

		surf = self.exp.render(cursor_path)

		w = surf.get_width()
		h = surf.get_height() + 2 * abs(self.offset)
		out = pygame.Surface((w, h), pygame.SRCALPHA)

		out.blit(surf, (0, (h - surf.get_height())//2 - self.offset))

		return out

class EmptyExpression(Expression):
	exp: None
	surf = pygame.Surface((0, 0))

	def render(self, cursor_path):
		print('render', self, cursor_path)

		return self.surf

if __name__ == '__main__':
	from pygame.locals import *

	pygame.font.init()
	font  = pygame.font.Font('../Product Sans Regular.ttf', 32)
	efont = pygame.font.Font('../Product Sans Regular.ttf', 24)
	sfont = pygame.font.Font('../Product Sans Regular.ttf', 12)

	c = type('c', (), {'__matmul__': (lambda s, x: (*x.to_bytes(3, 'big'),)), '__sub__': (lambda s, x: (x&255,)*3)})()
	bg = c-34
	fg = c@0xff9088
	green = c@0xa0ffe0

	fps = 60

	w, h = res = (1280, 720)

	def updateStat(msg = None, update = True):
		rect = (0, h-20, w, 21)
		display.fill(c-0, rect)

		tsurf = sfont.render(msg or f'{pos}', True, c--1)
		display.blit(tsurf, (5, h-20))

		if update: pygame.display.update(rect)

	def resize(size):
		global w, h, res, display
		w, h = res = size
		display = pygame.display.set_mode(res, RESIZABLE)
		updateDisplay()

	def updateDisplay():
		display.fill(bg)

		global surf_cache, cursor_path

		if surf_cache is None:
			surf_cache = curr_exp.render(cursor_path)
		x = (w - surf_cache.get_width()) // 2
		y = (h - surf_cache.get_height()) // 2
		display.blit(surf_cache, (x, y))

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
			Expression('1 + ', font, fg),
			FractionExpression((
				Expression('1', font, fg),
				Expression('22', font, fg),
			), font, fg),
			Expression(' + 0.34', font, fg),
			SubscriptExpression(
				Expression('5', efont, fg), font, fg, 15
			),
		), font, fg)

	cursor_path = [1, 1, len(curr_exp.exp[1].exp)]

	surf_cache = None

	print(cursor_path)

	resize(res)
	pres = pygame.display.list_modes()[0]
	clock = pygame.time.Clock()
	running = True
	while running:
		for event in pygame.event.get():
			if event.type == KEYDOWN:
				if   event.key == K_ESCAPE: running = False
				elif event.key == K_F11: toggleFullscreen()
				
				elif event.key == K_LEFT:
					path_len = len(cursor_path)
					cursor_path = curr_exp.cursor_prev(cursor_path)
					if cursor_path is None:
						cursor_path = curr_exp.cursor_first()
					print(cursor_path)
					surf_cache = None

				elif event.key == K_RIGHT:
					cursor_path = curr_exp.cursor_next(cursor_path)
					if cursor_path is None:
						cursor_path = curr_exp.cursor_last()
					print(cursor_path)
					surf_cache = None

				elif event.mod & (KMOD_LCTRL|KMOD_RCTRL):
					if event.key == K_BACKSPACE:
						inner_exp = cursor_path[-2]
						split = inner_exp.exp.rsplit(maxsplit=1)
						if len(split) <= 1: inner_exp.exp = ''
						else: inner_exp.exp = split[0]
						surf_cache = None
				elif event.key == K_BACKSPACE:
					inner_exp = cursor_path[-2]
					inner_exp.exp = inner_exp.exp[:-1]
					cursor -= 1
					inner_exp.exp = inner_exp.exp[:cursor][:-1] + inner_exp.exp[cursor:]

					surf_cache = None
				elif event.unicode and event.unicode.isprintable():
					inner_exp = curr_exp[cursor_path[:-1]]
					cursor = cursor_path[-1]
					inner_exp.exp = inner_exp.exp[:cursor] + event.unicode + inner_exp.exp[cursor:]
					cursor_path[-1] = cursor + 1

					surf_cache = None

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

