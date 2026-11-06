"""enlistment_screen.py - Pilot Callsign Creation & Super Earth Contract of Employment.

Renders an interactive military enlistment terminal displaying the official
Super Earth Armed Forces Contract of Employment, callsign/username entry,
and patriotic oath signing before deployment to the Naval Academy.
"""

import pygame
from typing import List, Optional, Tuple

from eagle1.data.player_profile import PlayerProfileManager
from eagle1.ui import theme, widgets
from eagle1.ui.menu_nav import MenuButton, VARIANT_DANGER, VARIANT_PRIMARY

try:
    from eagle1.systems.audio_manager import get_audio_manager
except ImportError:
    get_audio_manager = None

# Style flag for contract section headers. wrapped_lines stores (text, color); the draw code
# picks the header font by comparing against this constant, so it must never equal a body color.
CONTRACT_HEADER_COLOR = theme.ACCENT
CONTRACT_BODY_COLOR = theme.TEXT
CONTRACT_BREACH_COLOR = theme.lerp_color(theme.DANGER, theme.TEXT, 0.3)

CONTRACT_TEXT = """CONTRACT OF EMPLOYMENT
The following contract is made between and entered into by The Helldivers Division of the Super Earth Armed Forces (hereby referred to as "the Enlister") and the individual who has successfully completed their preliminary Helldiver training as set forth in Exhibit A of the Super Earth Armed Forces Recruitment and Retention Manual part 27/B-10264 (hereby referred to as "the Enlisted"). The following contract is entered into willingly, and the Enlisted confirms that they have authority to enter into such an agreement at this time, being of sound mind and body, of legal age, and of Citizenship Grade E or above.

1 SERVICES
1.1 The Enlisted shall perform the Services outlined in Appendix A in accordance with the operational directives identified by (i) Super Earth High Command (ii) the President of Super Earth (iii) the Democratic Council of Super Earth (iv) accredited employees of the Ministries of Super Earth (v) accredited representatives of the parties aforementioned in clauses 1.1.i - 1.1.v, (vi) accredited representatives of those representatives (hereby referred to as "the Authorized Command Structure"). The Authorized Command Structure may, at any point, with no prior notice, make amendments to the schedule of services outlined in Appendix A. A copy of Appendix A may, if required, be obtained by the Enlisted through contacting the relevant authorities in the SEAF Administrative Corps, with a hard copy of the Appendix to be delivered to the requesting Enlisted within 5-10 business years.
1.2 The Services performed by the Enlisted for the Enlister shall include, but are not limited to active combat operations (which may include, but shall not be limited to raids, deployments, invasions, sorties, forays, assaults, blitzes, incursions, onslaughts, liberations, razings, flattenings, and nukings), non-combat operations (which may include but shall not be limited to parades, interviews, signings and appearances, executions (both summary and otherwise), interplanetary transportation, including the escort of civilian or Democratic vessels, and any activities deemed necessary in the pursuit of the aims identified by (i) The Enlister, and (ii) The Authorized Command Structure. In order to enable full and complete enactment of these Services, the Enlisted is hereby authorized to employ lethal force, non-lethal force, non-lethal non-force, and lethal non-force, to be employed at the discretion of the Enlisted. The Enlisted may not subcontract in whole or in part any of the duties requested of them by the Enlister.
1.3 The Services shall be performed by the Enlisted at locations identified by (i) The Enlister (ii) The Authorized Command Structure. In order to enable the completion of the Services in an efficient and timely manner, the Enlisted will be entrusted with the command of a Class 6 "Super Destroyer" Series Crewed Interplanetary Combat Vessel (hereby referred to as "The Super Destroyer") Upon the Termination of the Contract of the Enlisted (refer to Section 5, TERMINATION), command of this Super Destroyer will be transferred to the next eligible Enlisted in the order designated by (i) the serving Ship Master, (ii) The Enlister, (iii) the Authorized Command Structure, (iv) Accredited representatives of the parties listed in clauses 1.3.i - 1.3.iii. The heirs, successors, and assigns of The Enlisted have no right, claim or interest in the ownership or command of the Super Destroyer. Should the actions of the Enlisted result in loss, damages, or impediments to the Super Destroyer, requiring ameliorative or restorative action, the cost of such repairs shall be subtracted from the Martyrdom Payment due to the heirs or successors of the Enlisted (refer to Section 2 COMPENSATION).
1.4 The Enlisted will be responsible for the purchasing, maintenance, replacement, and improvement of the equipment used for the provision of services. If the contract of the Enlisted is terminated due to the conditions outlined in Clause 5.1 (absence of pulse), the equipment purchased, maintained, replaced, and improved by the Enlisted shall stay with Destroyer, and shall be made available to the next Helldiver to command the vessel.

2 REMUNERATION
2.1 For the performance of the services outlined within the schedule set forth in Appendix A, the Helldiver shall receive monetary compensation for the services rendered. The compensation shall vary in line with the services performed. The Enlister reserves the right to, at any time and with no prior notice, make amendments to the schedule of payments.
2.2 The Enlister acknowledges that the position of the Enlisted ("Helldiver") is classified by the Super Earth Ministry of Employment as an "Exceptionally Patriotic Duty". Accordingly, upon commencement of the delivery of services, the immediate family members of the Enlisted (defined as parents, siblings, heirs, and successors) shall receive 4.5 citizenship points, to be allocated at the recipients' discretion. This compensation shall be non-transferable, and may not be exchanged for a cash equivalent.
2.3 In the event of the non-continuation of the 'alive' status of the Enlisted in the course of the rendition of services, a Martyrdom Payment shall be made to the immediate family members of the Enlisted (defined as parents, siblings, heirs, and successors) minus any dispensations outlined in Section 1.3.

3 CONFIDENTIALITY AND CLASSIFIED MATERIALS
3.1 In the course of the rendition of services, the Enlisted is likely to become exposed to information of strategic importance (including but not limited to maps, mission briefings, internal procedural documentation, details of products, prices, and seasonal discounts). The Enlister and Enlisted agree that any and all privileged information (collectively "CLASSIFIED MATERIALS") viewed by the Enlisted (i) shall be maintained in the strictest secrecy by the Enlisted, with all reasonable efforts made to avoid the transfer, leakage, dissemination, publication, conveyance, and/or seepage of Classified Materials, and (ii) shall be provided in formats which are traceable to the Enlisted in the event of transfer, leakage, dissemination, publication, conveyance, and/or seepage. The Enlisted agrees to return any and all data, documents, directories, manuals, maps, and notes pertaining to "CLASSIFIED MATERIALS" upon (i) termination of this contract, (ii) request by the Enlister.
3.2 Any information made known to the Enlisted outside of operational parameters which is not considered customarily known to the general citizenry and/or which was not known to the Enlisted prior to the commencement of this agreement shall, for the purposes of clarity, be considered "CONTROLLED CLASSIFIED MATERIALS". For the access of "CONTROLLED CLASSIFIED MATERIALS" explicit, advance written consent must be obtained by the Enlisted.
3.3 To read these terms and conditions in full shall be considered a breach of Clause 3.2.

4 INDEMNIFICATION
4.1 Unless otherwise stated, the Enlisted shall be solely and exclusively responsible for any and all damages, harm, liability, loss, costs, expenses, craters, atrocities, and crimes (civil, uncivil, war) caused, created, or generated during the course of the rendition of services. The Enlisted hereby indemnifies (i) The Enlister, and (ii) the Authorized Command Structure, including but not limited to any employees, representatives, heirs, and successors against any costs, challenges, losses, damages, or expenses (without limitation) arising from or relating in any way to the rendition of services by the Enlisted.
4.2 Any damage sustained by the Enlisted, whether reputational or corporeal (including but not limited to incineration, evisceration, spinal separation, vaporization, crushing, freezing, burning, decapitation, paper cuts, explosion, contusion, removal of arms and/or limbs, addition of arms and/or limbs, dizziness, nausea, shortness of breath and/or death) shall not be considered the responsibility of the Enlister.
4.3 The Enlisted shall not hold the Enlister in whole or in part responsible for whether they return in whole or in part.

5 TERMINATION
This agreement will be governed by the laws of Super Earth, and shall be terminated in the event that:
(i) The Enlisted is mortally wounded, such that medical attention shall not be physically or financially justifiable.
(ii) The Enlisted expresses seditious, dangerous, or Traitorous thoughts, opinions, actions or sentiments.
(iii) By the Enlister, for any reason. Notice of the cause for termination is not required. The provisions of sections 1, 2, 3, 4, and 6 shall survive termination.

6 GENERAL PROVISIONS
6.1 The Enlisted consents to personal information (including but not limited to Biometric, Patriotic, and Demographic data) to be collected and processed by (i) the Enlister (ii) The Authorized Command Structure (iii) Appropriate agents of the Super Earth Armed Forces and Democratic Council.
6.2 The Enlisted consents to personal samples (including but not limited to flesh, bone, and blood) to be collected and processed by (i) the Enlister (ii) The Authorized Command Structure (iii) Appropriate agents of the Super Earth Armed Forces and Democratic Council.
6.3 The Enlisted provides unequivocal and irrevocable consent to the use of experimental weaponries, technologies, and narcotics.
6.4 The Contract shall be considered binding upon being read, in whole or in part.
(For the purpose of the elimination of doubt, the Enlisted spending 1 second within 15 meters of a copy of the contract shall be interpreted as the contract being read.)"""

class EnlistmentScreen:
    """Interactive enlistment terminal handling username input, contract viewing, and signing."""

    MAX_USERNAME_LENGTH = 18

    def __init__(self, screen_w: int = 1280, screen_h: int = 720):
        self.screen_w = screen_w
        self.screen_h = screen_h

        self.username = ""
        self.error_message = ""
        self.input_focused = True
        self.scroll_offset = 0
        self.is_dragging_scrollbar = False

        self.profile_manager = PlayerProfileManager()
        self.audio = get_audio_manager() if get_audio_manager else None
        sfx = self.audio.play_sfx if self.audio else None

        # Pre-calculated geometry
        self.panel_x = 110
        self.panel_w = self.screen_w - 220
        self.outer_rect = pygame.Rect(self.panel_x - 10, 30, self.panel_w + 20, 650)

        # Input field rect
        self.input_rect = pygame.Rect(self.panel_x + 300, 110, 480, 46)

        # Contract container rect (starts below the validation message line)
        self.contract_rect = pygame.Rect(self.panel_x, 190, self.panel_w, 405)
        self.header_bar_rect = pygame.Rect(self.contract_rect.x, self.contract_rect.y, self.contract_rect.w, 36)
        self.text_area_rect = pygame.Rect(
            self.contract_rect.x + 24, self.contract_rect.y + 45, self.contract_rect.w - 60, 350
        )

        # Scrollbar geometry
        self.scrollbar_track = pygame.Rect(
            self.contract_rect.right - 26, self.text_area_rect.y, 14, self.text_area_rect.h
        )

        # Buttons rects
        self.btn_back_rect = pygame.Rect(self.panel_x, 615, 260, 48)
        self.btn_sign_rect = pygame.Rect(self.panel_x + 290, 615, self.panel_w - 290, 48)
        self._btn_back = MenuButton("CANCEL", self.btn_back_rect, hotkey="ESC", variant=VARIANT_DANGER, on_sfx=sfx)
        self._btn_sign = MenuButton(
            "SIGN CONTRACT", self.btn_sign_rect, hotkey="ENTER", variant=VARIANT_PRIMARY, on_sfx=sfx
        )

        # Fonts
        self.font_title = theme.get_font("display")
        self.font_sub = theme.get_font("mono_small")
        self.font_body = theme.get_font("body")
        self.font_header = theme.get_font("label")
        self.font_btn = theme.get_font("heading")
        self.font_input = theme.load_font(theme.ROLE_MONO, 22)
        self._fonts_ready = None not in (
            self.font_title, self.font_sub, self.font_body, self.font_header, self.font_btn, self.font_input
        )

        self._cache = widgets.TextCache(512)
        self._overlay = widgets.make_overlay((self.screen_w, self.screen_h), theme.OVERLAY_RGBA)
        self._error_rect: Optional[pygame.Rect] = None

        # Line wrap contract text
        self.line_height = (self.font_body.get_linesize() + 2) if self._fonts_ready else 22
        self.wrapped_lines = self._wrap_contract_text(CONTRACT_TEXT, self.text_area_rect.w) if self._fonts_ready else []
        self.visible_lines = self.text_area_rect.h // self.line_height
        self.max_scroll = max(0, len(self.wrapped_lines) - self.visible_lines)

        self._static: List[Tuple[pygame.Surface, Tuple[int, int]]] = []
        if self._fonts_ready:
            self._build_static_text()

    def _build_static_text(self) -> None:
        """Pre-render all unchanging text once."""
        cx = self.screen_w // 2
        title = self.font_title.render(
            widgets.fit_text(self.font_title, "SUPER EARTH ARMED FORCES — PILOT ENLISTMENT DIVISION", self.panel_w),
            True, theme.INFO,
        )
        sub = self.font_sub.render("MINISTRY OF DEFENSE // RECRUITMENT AND RETENTION BRANCH", True, theme.ACCENT)
        label = self.font_header.render("PILOT CALLSIGN:", True, theme.TEXT)
        header = self.font_header.render("EXHIBIT A: CONTRACT OF EMPLOYMENT — SEAF CODE 27/B-10264", True, theme.ACCENT)
        badge = self.font_sub.render("[CITIZENSHIP GRADE E REQUIRED]", True, theme.INFO)
        oath = self.font_sub.render("I SWEAR FEALTY TO MANAGED DEMOCRACY", True, theme.TEXT_MUTED)
        self._static = [
            (title, title.get_rect(center=(cx, 58)).topleft),
            (sub, sub.get_rect(center=(cx, 92)).topleft),
            (label, (self.input_rect.x - label.get_width() - 16, self.input_rect.centery - label.get_height() // 2)),
            (header, (self.header_bar_rect.x + 16, self.header_bar_rect.centery - header.get_height() // 2)),
            (badge, (self.header_bar_rect.right - badge.get_width() - 16,
                     self.header_bar_rect.centery - badge.get_height() // 2)),
            (oath, oath.get_rect(midbottom=(cx, self.btn_sign_rect.y - 4)).topleft),
        ]

    def _wrap_contract_text(self, text: str, max_w: int) -> List[Tuple[str, Tuple[int, int, int]]]:
        """Wrap contract text lines with styling colors for headers vs body."""
        wrapped = []
        header_prefixes = (
            "CONTRACT", "1 SERVICES", "2 REMUNERATION", "3 CONFIDENTIALITY",
            "4 INDEMNIFICATION", "5 TERMINATION", "6 GENERAL PROVISIONS",
        )

        for para in text.split("\n"):
            if not para.strip():
                wrapped.append(("", theme.TEXT_MUTED))
                continue

            if para.startswith(header_prefixes):
                wrapped.append((para, CONTRACT_HEADER_COLOR))
                continue

            words = para.split(" ")
            current_line = ""
            for word in words:
                test_line = f"{current_line} {word}".strip()
                if self.font_body.size(test_line)[0] <= max_w:
                    current_line = test_line
                else:
                    if current_line:
                        wrapped.append((current_line, self._body_color(current_line)))
                    current_line = word
            if current_line:
                wrapped.append((current_line, self._body_color(current_line)))

        return wrapped

    @staticmethod
    def _body_color(line: str) -> Tuple[int, int, int]:
        lowered = line.lower()
        if "breach" in lowered or "binding upon" in lowered or "1 second within 15 meters" in lowered:
            return CONTRACT_BREACH_COLOR
        return CONTRACT_BODY_COLOR

    def reset(self):
        """Reset screen state when opening."""
        self.username = ""
        self.error_message = ""
        self.scroll_offset = 0
        self.input_focused = True
        self.is_dragging_scrollbar = False

    def handle_event(self, event: pygame.event.Event, mouse_pos: Optional[Tuple[int, int]] = None) -> Optional[str]:
        """Process keyboard, mouse clicks, and scroll wheel events.

        Returns:
            "start_academy": If contract was accepted and profile created.
            "back": If user cancelled and requested return to main menu.
            None: If input processed internally.
        """
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()

        # Mouse wheel scrolling
        if event.type == pygame.MOUSEWHEEL:
            self.scroll_offset = max(0, min(self.max_scroll, self.scroll_offset - event.y * 3))
            return None

        # Mouse button interactions
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.input_focused = self.input_rect.collidepoint(mouse_pos)

            # Check scrollbar track click
            if self.scrollbar_track.collidepoint(mouse_pos):
                thumb_y, thumb_h = self._get_scrollbar_thumb()
                if thumb_y <= mouse_pos[1] <= thumb_y + thumb_h:
                    self.is_dragging_scrollbar = True
                else:
                    # Jump scroll towards click
                    rel_y = mouse_pos[1] - self.scrollbar_track.y
                    ratio = rel_y / float(self.scrollbar_track.h)
                    self.scroll_offset = max(0, min(self.max_scroll, int(ratio * self.max_scroll)))
                return None

            # Check buttons
            if self.btn_back_rect.collidepoint(mouse_pos):
                if self.audio:
                    self.audio.play_sfx("ui_click")
                return "back"

            if self.btn_sign_rect.collidepoint(mouse_pos):
                return self._attempt_sign()

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.is_dragging_scrollbar = False

        elif event.type == pygame.MOUSEMOTION and self.is_dragging_scrollbar:
            rel_y = mouse_pos[1] - self.scrollbar_track.y
            ratio = max(0.0, min(1.0, rel_y / float(self.scrollbar_track.h)))
            self.scroll_offset = max(0, min(self.max_scroll, int(ratio * self.max_scroll)))

        # Keyboard typing & navigation
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.audio:
                    self.audio.play_sfx("ui_click")
                return "back"

            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return self._attempt_sign()

            elif event.key == pygame.K_TAB:
                self.input_focused = not self.input_focused
            elif event.key == pygame.K_UP:
                self.scroll_offset = max(0, self.scroll_offset - 2)
            elif event.key == pygame.K_DOWN:
                self.scroll_offset = max(0, min(self.max_scroll, self.scroll_offset + 2))
            elif event.key == pygame.K_PAGEUP:
                self.scroll_offset = max(0, self.scroll_offset - self.visible_lines)
            elif event.key == pygame.K_PAGEDOWN:
                self.scroll_offset = max(0, min(self.max_scroll, self.scroll_offset + self.visible_lines))
            elif event.key == pygame.K_BACKSPACE:
                if self.input_focused and self.username:
                    self.username = self.username[:-1]
                    self.error_message = ""
            else:
                # Accept typing characters; typing while unfocused re-focuses the field
                char = event.unicode
                if char and char.isprintable() and len(self.username) < self.MAX_USERNAME_LENGTH:
                    self.input_focused = True
                    self.username += char.upper()
                    self.error_message = ""

        return None

    def _attempt_sign(self) -> Optional[str]:
        """Validate callsign and persist player profile."""
        clean_name = self.username.strip()
        if not clean_name:
            self.error_message = "CALLSIGN REQUIRED — ENTER PILOT NAME TO ENLIST"
            if self.audio:
                self.audio.play_sfx("player_damage")
            return None

        # Create profile
        self.profile_manager.create_profile(clean_name, citizenship_grade="E")
        if self.audio:
            self.audio.play_sfx("ui_click")
        return "start_academy"

    def _get_scrollbar_thumb(self) -> Tuple[int, int]:
        """Compute the vertical position and height of the scrollbar thumb."""
        if len(self.wrapped_lines) <= self.visible_lines:
            return self.scrollbar_track.y, self.scrollbar_track.h

        track_h = self.scrollbar_track.h
        thumb_h = max(24, int(track_h * (self.visible_lines / len(self.wrapped_lines))))
        travel = track_h - thumb_h
        thumb_y = self.scrollbar_track.y + int(travel * (self.scroll_offset / float(self.max_scroll)))
        return thumb_y, thumb_h

    def draw(self, surface: pygame.Surface, mouse_pos: Optional[Tuple[int, int]] = None):
        """Render the complete Enlistment Screen and interactive controls."""
        if mouse_pos is None:
            mouse_pos = pygame.mouse.get_pos()

        surface.blit(self._overlay, (0, 0))
        if not self._fonts_ready:
            return

        widgets.draw_panel(surface, self.outer_rect, theme.PANEL, theme.BORDER_STRONG, theme.ACCENT)
        for surf, pos in self._static[:3]:
            surface.blit(surf, pos)

        # Callsign Input Field
        widgets.draw_panel(
            surface, self.input_rect, theme.PANEL_RAISED,
            theme.ACCENT if self.input_focused else theme.BORDER_STRONG, brackets=False,
        )
        display_text = self.username
        if self.input_focused and ((pygame.time.get_ticks() // 450) % 2 == 0):
            display_text += "_"
        text_surf = self._cache.render(self.font_input, display_text, theme.TEXT)
        surface.blit(text_surf, (self.input_rect.x + 14, self.input_rect.centery - text_surf.get_height() // 2))

        # Error / Validation Warning below the input field (always on screen)
        self._error_rect = None
        if self.error_message:
            msg = widgets.fit_text(self.font_sub, self.error_message, self.contract_rect.w)
            err_surf = self._cache.render(self.font_sub, msg, theme.DANGER)
            self._error_rect = err_surf.get_rect(midtop=(self.input_rect.centerx, self.input_rect.bottom + 6))
            surface.blit(err_surf, self._error_rect)

        # Contract container with header bar
        widgets.draw_panel(surface, self.contract_rect, theme.PANEL, theme.ACCENT_DIM, theme.ACCENT)
        pygame.draw.rect(surface, theme.PANEL_RAISED, self.header_bar_rect)
        pygame.draw.line(
            surface, theme.ACCENT_DIM, (self.header_bar_rect.x, self.header_bar_rect.bottom),
            (self.header_bar_rect.right, self.header_bar_rect.bottom), 2,
        )
        for surf, pos in self._static[3:5]:
            surface.blit(surf, pos)

        # Visible contract lines with clipping
        orig_clip = surface.get_clip()
        surface.set_clip(self.text_area_rect)
        y_pos = self.text_area_rect.y
        end_idx = min(len(self.wrapped_lines), self.scroll_offset + self.visible_lines + 1)
        for i in range(self.scroll_offset, end_idx):
            line_text, line_color = self.wrapped_lines[i]
            if line_text:
                font = self.font_header if line_color == CONTRACT_HEADER_COLOR else self.font_body
                surface.blit(self._cache.render(font, line_text, line_color), (self.text_area_rect.x, y_pos))
            y_pos += self.line_height
        surface.set_clip(orig_clip)

        # Scrollbar
        pygame.draw.rect(surface, theme.PANEL_RAISED, self.scrollbar_track)
        thumb_y, thumb_h = self._get_scrollbar_thumb()
        thumb_rect = pygame.Rect(self.scrollbar_track.x, thumb_y, self.scrollbar_track.w, thumb_h)
        active = self.is_dragging_scrollbar or thumb_rect.collidepoint(mouse_pos)
        pygame.draw.rect(surface, theme.ACCENT if active else theme.BORDER_STRONG, thumb_rect)

        # Oath line and buttons
        surface.blit(*self._static[5])
        self._btn_back.draw(surface, mouse_pos)
        self._btn_sign.draw(surface, mouse_pos)
