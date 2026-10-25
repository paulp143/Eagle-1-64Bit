"""enlistment_screen.py - Pilot Callsign Creation & Super Earth Contract of Employment.

Renders an interactive military enlistment terminal displaying the official
Super Earth Armed Forces Contract of Employment, callsign/username entry,
and patriotic oath signing before deployment to the Naval Academy.
"""

import pygame
from typing import List, Optional, Tuple

from eagle1.data.player_profile import PlayerProfileManager

try:
    from eagle1.systems.audio_manager import get_audio_manager
except Exception:
    get_audio_manager = None


def _get_font(name: str, size: int, bold: bool = False) -> pygame.font.Font:
    """Safe font loader with Fallback for headless environments."""
    if not pygame.font.get_init():
        try:
            pygame.font.init()
        except Exception:
            pass
    try:
        return pygame.font.SysFont(name, size, bold=bold)
    except Exception:
        return pygame.font.Font(None, size)


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

        # Pre-calculated geometry
        self.panel_x = 110
        self.panel_w = self.screen_w - 220

        # Input field rect
        self.input_rect = pygame.Rect(self.panel_x + 300, 110, 480, 46)

        # Contract container rect
        self.contract_rect = pygame.Rect(self.panel_x, 175, self.panel_w, 420)
        self.text_area_rect = pygame.Rect(self.contract_rect.x + 24, self.contract_rect.y + 45, self.contract_rect.w - 60, 355)

        # Scrollbar geometry
        self.scrollbar_track = pygame.Rect(self.contract_rect.right - 26, self.text_area_rect.y, 14, self.text_area_rect.h)

        # Buttons rects
        self.btn_back_rect = pygame.Rect(self.panel_x, 615, 260, 48)
        self.btn_sign_rect = pygame.Rect(self.panel_x + 290, 615, self.panel_w - 290, 48)

        # Fonts
        self.font_title = _get_font("arial", 28, bold=True)
        self.font_sub = _get_font("arial", 16, bold=True)
        self.font_body = _get_font("arial", 15)
        self.font_header = _get_font("arial", 16, bold=True)
        self.font_btn = _get_font("arial", 18, bold=True)
        self.font_input = _get_font("courier,monospace", 22, bold=True)

        # Line wrap contract text
        self.line_height = 22
        self.wrapped_lines = self._wrap_contract_text(CONTRACT_TEXT, self.text_area_rect.w)
        self.visible_lines = self.text_area_rect.h // self.line_height
        self.max_scroll = max(0, len(self.wrapped_lines) - self.visible_lines)

    def _wrap_contract_text(self, text: str, max_w: int) -> List[Tuple[str, Tuple[int, int, int]]]:
        """Wrap contract text lines with styling colors for headers vs body."""
        wrapped = []
        raw_paragraphs = text.split("\n")

        for para in raw_paragraphs:
            if not para.strip():
                wrapped.append(("", (200, 200, 200)))
                continue

            # Section headers
            if para.startswith("CONTRACT") or para.startswith("1 SERVICES") or para.startswith("2 REMUNERATION") or \
               para.startswith("3 CONFIDENTIALITY") or para.startswith("4 INDEMNIFICATION") or \
               para.startswith("5 TERMINATION") or para.startswith("6 GENERAL PROVISIONS"):
                wrapped.append((para, (255, 215, 0)))  # Gold
                continue

            words = para.split(" ")
            current_line = ""
            for word in words:
                test_line = f"{current_line} {word}".strip()
                if self.font_body.size(test_line)[0] <= max_w:
                    current_line = test_line
                else:
                    if current_line:
                        color = (255, 120, 120) if "breach" in current_line.lower() or "binding upon" in current_line.lower() else (220, 225, 235)
                        wrapped.append((current_line, color))
                    current_line = word
            if current_line:
                color = (255, 120, 120) if "breach" in current_line.lower() or "1 second within 15 meters" in current_line.lower() else (220, 225, 235)
                wrapped.append((current_line, color))

        return wrapped

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
            # Check input field focus
            if self.input_rect.collidepoint(mouse_pos):
                self.input_focused = True
            else:
                self.input_focused = False

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

            elif event.key == pygame.K_UP:
                self.scroll_offset = max(0, self.scroll_offset - 2)
            elif event.key == pygame.K_DOWN:
                self.scroll_offset = max(0, min(self.max_scroll, self.scroll_offset + 2))
            elif event.key == pygame.K_PAGEUP:
                self.scroll_offset = max(0, self.scroll_offset - self.visible_lines)
            elif event.key == pygame.K_PAGEDOWN:
                self.scroll_offset = max(0, min(self.max_scroll, self.scroll_offset + self.visible_lines))

            elif self.input_focused:
                if event.key == pygame.K_BACKSPACE:
                    if self.username:
                        self.username = self.username[:-1]
                        self.error_message = ""
                        if self.audio:
                            self.audio.play_sfx("ui_hover")
                else:
                    # Accept typing characters
                    char = event.unicode
                    if char and char.isprintable() and len(self.username) < self.MAX_USERNAME_LENGTH:
                        self.username += char.upper()
                        self.error_message = ""
                        if self.audio:
                            self.audio.play_sfx("ui_hover")

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

        # Dark tactical background overlay
        overlay = pygame.Surface((self.screen_w, self.screen_h), pygame.SRCALPHA)
        overlay.fill((8, 12, 18, 245))
        surface.blit(overlay, (0, 0))

        # Main frame panel
        outer_rect = pygame.Rect(self.panel_x - 10, 30, self.panel_w + 20, 650)
        pygame.draw.rect(surface, (14, 20, 32), outer_rect, border_radius=12)
        pygame.draw.rect(surface, (0, 180, 240), outer_rect, width=2, border_radius=12)

        # Screen header
        title_surf = self.font_title.render("SUPER EARTH ARMED FORCES — PILOT ENLISTMENT DIVISION", True, (0, 230, 255))
        surface.blit(title_surf, title_surf.get_rect(center=(self.screen_w // 2, 60)))

        sub_surf = self.font_sub.render("MINISTRY OF DEFENSE // RECRUITMENT AND RETENTION BRANCH", True, (255, 215, 0))
        surface.blit(sub_surf, sub_surf.get_rect(center=(self.screen_w // 2, 92)))

        # Callsign Label
        label_surf = self.font_header.render("PILOT CALLSIGN:", True, (240, 245, 255))
        surface.blit(label_surf, (self.panel_x + 120, 122))

        # Callsign Input Field
        input_border_color = (0, 240, 255) if self.input_focused else (80, 110, 150)
        pygame.draw.rect(surface, (18, 26, 42), self.input_rect, border_radius=8)
        pygame.draw.rect(surface, input_border_color, self.input_rect, width=2, border_radius=8)

        # Callsign Text + Blinking Cursor
        display_text = self.username
        show_cursor = self.input_focused and ((pygame.time.get_ticks() // 450) % 2 == 0)
        if show_cursor:
            display_text += "_"

        text_surf = self.font_input.render(display_text, True, (255, 255, 255))
        surface.blit(text_surf, (self.input_rect.x + 14, self.input_rect.y + 11))

        # Error / Validation Warning
        if self.error_message:
            err_surf = self.font_sub.render(self.error_message, True, (255, 75, 75))
            surface.blit(err_surf, (self.input_rect.right + 20, 123))

        # Contract Container
        pygame.draw.rect(surface, (12, 16, 26), self.contract_rect, border_radius=8)
        pygame.draw.rect(surface, (200, 160, 40), self.contract_rect, width=2, border_radius=8)

        # Contract Header Banner
        header_bar_rect = pygame.Rect(self.contract_rect.x, self.contract_rect.y, self.contract_rect.w, 36)
        pygame.draw.rect(surface, (24, 32, 50), header_bar_rect, border_top_left_radius=8, border_top_right_radius=8)
        pygame.draw.line(surface, (200, 160, 40), (header_bar_rect.x, header_bar_rect.bottom), (header_bar_rect.right, header_bar_rect.bottom), 2)

        c_header_surf = self.font_header.render("EXHIBIT A: CONTRACT OF EMPLOYMENT — SEAF CODE 27/B-10264", True, (255, 225, 80))
        surface.blit(c_header_surf, (header_bar_rect.x + 16, header_bar_rect.y + 8))

        badge_surf = self.font_sub.render("[CITIZENSHIP GRADE E REQUIRED]", True, (0, 220, 255))
        surface.blit(badge_surf, (header_bar_rect.right - badge_surf.get_width() - 16, header_bar_rect.y + 9))

        # Render visible contract lines with clipping
        clip_rect = self.text_area_rect
        orig_clip = surface.get_clip()
        surface.set_clip(clip_rect)

        y_pos = self.text_area_rect.y
        start_idx = self.scroll_offset
        end_idx = min(len(self.wrapped_lines), start_idx + self.visible_lines + 1)

        for i in range(start_idx, end_idx):
            line_text, line_color = self.wrapped_lines[i]
            if line_text:
                font = self.font_header if line_color == (255, 215, 0) else self.font_body
                line_surf = font.render(line_text, True, line_color)
                surface.blit(line_surf, (self.text_area_rect.x, y_pos))
            y_pos += self.line_height

        surface.set_clip(orig_clip)

        # Scrollbar rendering
        pygame.draw.rect(surface, (20, 28, 44), self.scrollbar_track, border_radius=6)
        thumb_y, thumb_h = self._get_scrollbar_thumb()
        thumb_rect = pygame.Rect(self.scrollbar_track.x, thumb_y, self.scrollbar_track.w, thumb_h)
        thumb_color = (0, 210, 255) if (self.is_dragging_scrollbar or thumb_rect.collidepoint(mouse_pos)) else (80, 110, 150)
        pygame.draw.rect(surface, thumb_color, thumb_rect, border_radius=6)

        # Back Button
        back_hover = self.btn_back_rect.collidepoint(mouse_pos)
        back_bg = (50, 25, 30) if back_hover else (30, 20, 25)
        back_border = (255, 75, 75) if back_hover else (140, 70, 70)
        pygame.draw.rect(surface, back_bg, self.btn_back_rect, border_radius=8)
        pygame.draw.rect(surface, back_border, self.btn_back_rect, width=2, border_radius=8)
        back_text = self.font_btn.render("CANCEL [ESC]", True, (255, 220, 220))
        surface.blit(back_text, back_text.get_rect(center=self.btn_back_rect.center))

        # Sign Button
        sign_hover = self.btn_sign_rect.collidepoint(mouse_pos)
        sign_bg = (30, 80, 130) if sign_hover else (18, 45, 75)
        sign_border = (0, 240, 255) if sign_hover else (0, 170, 220)
        pygame.draw.rect(surface, sign_bg, self.btn_sign_rect, border_radius=8)
        pygame.draw.rect(surface, sign_border, self.btn_sign_rect, width=2, border_radius=8)

        sign_text = self.font_btn.render("I SWEAR FEALTY TO MANAGED DEMOCRACY & SIGN CONTRACT [ENTER]", True, (255, 240, 160))
        surface.blit(sign_text, sign_text.get_rect(center=self.btn_sign_rect.center))
