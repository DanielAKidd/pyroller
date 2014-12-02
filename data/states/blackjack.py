from random import choice
import pygame as pg
from .. import tools, prepare
from ..components.angles import get_distance, get_angle, project
from ..components.labels import Label, Button, PayloadButton, Blinker
from ..components.cards import Deck
from ..components.chips import ChipStack, ChipRack, cash_to_chips, chips_to_cash
from ..components.blackjack_dealer import Dealer
from ..components.blackjack_player import Player
from ..components.blackjack_hand import Hand
            

class Blackjack(tools._State):
    """State to represent a blackjack game. Player cash
        will be converted to chips for the game and converted
        back into cash before returning to the lobby."""
    def __init__(self):
        super(Blackjack, self).__init__()
        self.font = prepare.FONTS["Saniretro"]
        self.result_font = prepare.FONTS["Saniretro"]
        names = ["cardplace{}".format(x) for x in (2, 3, 4)]
        self.deal_sounds = [prepare.SFX[name] for name in names]
        names = ["chipsstack{}".format(x) for x in (3, 5, 6)]
        self.chip_sounds = [prepare.SFX[name] for name in names]
        self.screen_rect = pg.display.get_surface().get_rect()
        self.music_icon = prepare.GFX["speaker"]
        topright = (self.screen_rect.right - 10, self.screen_rect.top + 10)
        self.music_icon_rect = self.music_icon.get_rect(topright=topright)
        self.mute_icon = prepare.GFX["mute"]
        self.play_music = True
        self.game_started = False
        
        b_width = 240
        b_height = 60
        left, top = (555, 500)
        vert_space = 20
        font_size = 48
        action_texts = ("Hit", "Stand", "Double Down", "Split", "Insurance")
        labels = iter([Label(self.font, font_size, text, "gold3", {"center": (0, 0)})
                            for text in action_texts])
        self.hit_button = PayloadButton(left, top, b_width, b_height,
                                                       next(labels), self.hit)
        deal_label = Label(self.font, font_size, "Deal", "gold3", {"center": (0, 0)})
        self.deal_button = Button(left, top, b_width, b_height, deal_label)
        top += b_height + vert_space
        self.stand_button = PayloadButton(left, top, b_width, b_height, 
                                                            next(labels), self.stand)
        top += b_height + vert_space
        self.double_down_button = PayloadButton(left, top, b_width, b_height,
                                                                       next(labels), self.double_down)
        top += b_height + vert_space
        self.split_button = PayloadButton(left, top, b_width, b_height,
                                                          next(labels), self.split_hand)
        top += b_height + vert_space
        self.insurance_button = PayloadButton(left, top, b_width, b_height,
                                                                 next(labels), self.buy_insurance)
        self.player_buttons = [self.hit_button, self.stand_button, self.double_down_button,
                                         self.split_button, self.insurance_button]
        ng_label = Label(self.font, font_size, "New Game", "gold3", {"center": (0, 0)})
        self.new_game_button = Button(self.screen_rect.centerx - (b_width//2), 
                                                        self.screen_rect.bottom - (b_height + 15),
                                                        b_width, b_height, ng_label)
        lobby_label = Label(self.font, font_size, "Lobby", "gold3", {"center": (0, 0)})
        self.lobby_button = Button(20, self.screen_rect.bottom - (b_height + 15), 
                                                 b_width, b_height, lobby_label)
                                                
    def new_game(self, player_cash, chips=None):    
        """Start a new round of blackjack."""
        self.deck = Deck((50, 50), prepare.CARD_SIZE)
        self.dealer = Dealer()
        self.chip_rack = ChipRack((200, 20))
        self.moving_cards =  []
        self.moving_stacks = []
        self.player = Player(player_cash, chips)
        self.state = "Betting"
        for button in self.player_buttons:
            button.active = False
        self.hit_button.active = True
        self.stand_button.active = True
        self.current_player_hand = self.player.hands[0]
        self.game_started = True
        
    def startup(self, current_time, persistent):
        """Get state ready to resume."""
        self.persist = persistent
        self.casino_player = self.persist["casino_player"]
        if not self.game_started:
            self.new_game(self.casino_player.stats["cash"])
    
    def hit(self, player, hand):
        """Draw a card from deck and add to hand."""
        choice(self.deal_sounds).play()
        card = self.deck.draw_card()
        card.face_up = True
        card.destination = hand.slots[-1]
        self.moving_cards.append(card)

    def stand(self, player, hand):
        """Player is done with this hand."""
        hand.final = True

    def double_down(self, player, hand):
        """Double player's bet on the hand, deal one
        more card and finalize hand."""
        chip_total = player.get_chip_total()
        bet = sum([chip.value for chip in hand.bet])
        if chip_total >= bet:
            bet_chips = self.player.withdraw_chips(bet)
            hand.bet.extend(bet_chips)
            choice(self.deal_sounds).play()
            card = self.deck.draw_card()
            card.face_up = True
            card.destination = hand.slots[-1]
            self.moving_cards.append(card)
            hand.final = True
    
    def split_hand(self, player, hand):
        """Split player's hand into two hands, adjust hand locations
        and deal a new card to both hands."""
        chip_total = player.get_chip_total()
        bet = sum([chip.value for chip in hand.bet])
        if chip_total < bet:
            return
        if len(hand.cards) == 2:
            c1 = hand.card_values[hand.cards[0].value]
            c2 = hand.card_values[hand.cards[1].value]
            if c1 == c2:                
                hand.slots = hand.slots[:-1]
                self.player.move_hands(((self.screen_rect.left + 20) - hand.slots[0].left, 0))
                p_slot = player.hands[-1].slots[0]
                hand_slot = p_slot.move(int(prepare.CARD_SIZE[0] * 2.5), 0)
                card = hand.cards.pop()
                new_hand = Hand(hand_slot.topleft, [card])
                new_hand.slots = [hand_slot]
                card.rect.topleft = hand_slot.topleft
                player.hands.append(new_hand)
                player.add_slot(new_hand)
                new_hand.bet = self.player.withdraw_chips(bet)
                choice(self.deal_sounds).play()
                card1 = self.deck.draw_card()
                card1.destination = hand.slots[-1]
                card1.face_up = True
                choice(self.deal_sounds).play()
                card2 = self.deck.draw_card()
                card2.destination = new_hand.slots[-1]
                card2.face_up = True
                self.moving_cards.extend([card1, card2])
                
    def buy_insurance(self, player, hand):
        """Currently unimplemented."""
        chip_total = player.get_chip_total()
        bet = sum([chip.value for chip in hand.bet])
        if chip_total < bet//2:
            return
    
    def tally_hands(self):
        """Calculate result of each player hand and set appropriate
        flag for each hand."""
        if self.dealer.hand.blackjack:
            for hand in self.player.hands:
                hand.loser = True
        elif self.dealer.hand.busted:
            for hand in self.player.hands:
                if not hand.busted and not hand.blackjack:
                    hand.winner = True                         
        else:
            d_score = self.dealer.hand.best_score()
            for hand in self.player.hands:
                if not hand.busted:
                    p_score = hand.best_score()
                    if p_score == 21 and len(hand.cards) == 2:
                        hand.blackjack = True
                    elif p_score < d_score:
                        hand.loser = True
                    elif p_score == d_score:
                        hand.push = True
                    else:
                        hand.winner = True
                        
    def pay_out(self):
        """Calculate player win amounts, update stats and return chips
        totalling total win amount."""
        cash = 0
        for hand in self.player.hands:
            bet = sum([chip.value for chip in hand.bet])
            self.casino_player.stats["Blackjack"]["hands played"] += 1
            self.casino_player.stats["Blackjack"]["total bets"] += bet
            if hand.busted:
                self.casino_player.stats["Blackjack"]["busts"] += 1
                self.casino_player.stats["Blackjack"]["hands lost"] += 1
            elif hand.loser:
                self.casino_player.stats["Blackjack"]["hands lost"] += 1
            elif hand.blackjack:
                cash += int(bet + (bet * 1.5))
                self.casino_player.stats["Blackjack"]["blackjacks"] += 1
                self.casino_player.stats["Blackjack"]["hands won"] += 1  
            elif hand.winner:
                cash += bet * 2
                self.casino_player.stats["Blackjack"]["hands won"] += 1  
            elif hand.push:
                cash += bet
                self.casino_player.stats["Blackjack"]["pushes"] += 1
            elif self.dealer.hand.blackjack and hand.insurance:
                cash += sum([chip.value for chip in hand.insurance])
            
        self.casino_player.stats["Blackjack"]["total winnings"] += cash
        chips = cash_to_chips(cash)
        return chips
        
    def cash_out_player(self):
        """Convert player's chips to cash and update stats."""
        self.casino_player.stats["cash"] = self.player.get_chip_total()

    def get_event(self, event):
        if event.type == pg.QUIT:
            self.cash_out_player()
            self.game_started = False
            self.done = True
            self.next = "LOBBYSCREEN"
        elif event.type == pg.MOUSEBUTTONDOWN:
            if self.music_icon_rect.collidepoint(event.pos):
                self.play_music = not self.play_music
                if self.play_music:
                    pg.mixer.music.play(-1)
                else:
                    pg.mixer.music.stop()
            elif self.lobby_button.rect.collidepoint(event.pos):
                self.cash_out_player()
                self.game_started = False
                self.done = True
                self.next = "LOBBYSCREEN"
            
            if self.state == "Player Turn":
                if not self.moving_cards:
                    for button in self.player_buttons:
                        if button.active and button.rect.collidepoint(event.pos):
                            button.payload(self.player, self.current_player_hand)
            elif self.state == "Betting":
                if not self.moving_stacks:
                    if event.button == 1:
                        if self.deal_button.rect.collidepoint(event.pos):
                            if any(x.bet for x in self.player.hands):
                                self.state = "Dealing"
                                self.casino_player.stats["Blackjack"]["games played"] += 1
                        for stack in [x for x in self.player.chips.values() if x.chips]:
                            bet_chips = stack.grab_chips(event.pos)
                            if bet_chips is not None:
                                choice(self.chip_sounds).play()
                                self.moving_stacks.append(bet_chips)
                                break
 
                        for hand in self.player.hands:
                            removed = set()
                            for chip in hand.bet:
                                if chip.rect.collidepoint(event.pos):
                                    choice(self.chip_sounds).play()
                                    removed.add(chip)
                                    self.player.add_chips([chip])
                                    break
                            hand.bet = [x for x in hand.bet if x not in removed]
            elif self.state == "Show Results":
                if event.button == 1:
                    if self.new_game_button.rect.collidepoint(event.pos):
                        all_chips = []
                        for stack in self.player.chips.values():
                            all_chips.extend(stack.chips)
                        self.new_game(self.player.cash, all_chips)
        elif event.type == pg.MOUSEBUTTONUP:
            if self.moving_stacks:
                if event.button == 1:
                    for stack in self.moving_stacks:
                        stack.bottomleft = event.pos
                        if self.chip_rack.rect.collidepoint(event.pos):
                            self.player.add_chips(self.chip_rack.break_chips(stack.chips))
                        else:    
                            self.current_player_hand.bet.extend(stack.chips)
                    self.moving_stacks = []    
                    
    def update(self, surface, keys, current_time, dt):
        if self.state == "Betting":
            if not self.moving_stacks:
                pass
            else:
                for stack in self.moving_stacks:
                    x, y = pg.mouse.get_pos()
                    stack.bottomleft = (x - (prepare.CHIP_SIZE[0] // 2),
                                                 y + 6)
        elif self.state == "Dealing":
            if not self.moving_cards:
                if len(self.current_player_hand.cards) < 2:
                    choice(self.deal_sounds).play()
                    card = self.deck.draw_card()
                    card.face_up = True
                    card.destination = self.current_player_hand.slots[-1]
                    self.moving_cards.append(card)
                elif len(self.dealer.hand.cards) < 2:
                    choice(self.deal_sounds).play()
                    card = self.deck.draw_card()
                    if len(self.dealer.hand.cards) > 0:
                        card.face_up = True
                    card.destination = self.dealer.hand.slots[-1]
                    self.moving_cards.append(card)
                else:
                    self.state = "Player Turn"
        
        elif self.state == "Player Turn":
            self.split_button.active = False
            self.double_down_button.active = True
            self.insurance_button.active = False
            
            if not self.moving_cards:
                hand = self.current_player_hand
                hand_score = hand.best_score()
                if hand_score is None:
                    hand.busted = True
                    hand.final = True
                
                if len(hand.cards) == 2 and len(self.player.hands) < 2:
                    c1 = hand.card_values[hand.cards[0].value]
                    c2 = hand.card_values[hand.cards[1].value]
                    if c1 == c2:
                        self.split_button.active = True
                if (self.dealer.hand.cards[1].value == 14
                    and not hand.insurance):
                    self.insurance_button.active = True
                if len(hand.cards) == 2:
                    if hand_score == 21:
                        hand.blackjack = True
                        hand.final = True
                if hand.final:
                    if all([hand.final for hand in self.player.hands]):
                        self.dealer.hand.cards[0].face_up = True
                        self.state = "Dealer Turn"
                    else:
                        next_hand = [x for x in self.player.hands if not x.final][0]
                        self.current_player_hand = next_hand
        
        elif self.state == "Dealer Turn":
            if all([hand.busted for hand in self.player.hands]):
                self.dealer.hand.final = True
                self.state = "End Round"
                return
            if not self.moving_cards:
                hand_score = self.dealer.hand.best_score()
                if hand_score is None:
                    self.dealer.hand.busted = True
                    self.dealer.hand.final = True
                elif hand_score == 21 and len(self.dealer.hand.cards) == 2:
                    self.dealer.hand.blackjack = True
                    self.dealer.hand.final = True
                elif hand_score < 17:
                    self.hit(self.dealer, self.dealer.hand)
                else:
                    self.dealer.hand.final = True
                if self.dealer.hand.final:    
                    self.state = "End Round"
        
        elif self.state == "End Round":
            self.tally_hands()
            payout = self.pay_out()
            self.player.add_chips(payout)
            self.result_labels = []
            hands = self.player.hands[:]
            if self.dealer.hand.busted:
                hands.append(self.dealer.hand)
            if len(hands) >2:
                text_size = 64
            elif len(hands) == 2:
                text_size = 80
            else:
                text_size = 96
            for hand in hands:
                if hand.blackjack:
                    text, color = "Blackjack", "gold3"
                    text_size -= 8
                elif hand.winner:
                    text, color = "Win", "gold3"
                elif hand.push:
                    text, color = "Push", "gold3"
                elif hand.busted:
                    text, color = "Bust", "darkred"             
                else:
                    text, color = "Loss", "darkred"
                centerx = (hand.slots[0].left + hand.slots[-1].right) // 2
                centery = hand.slots[0].centery               
                label = Blinker(self.result_font, text_size, text, color, 
                                      {"center": (centerx, centery)},
                                      450)
                self.result_labels.append(label)
                hand.bet = []                
            self.state = "Show Results"

        arrived = set()
        for card in self.moving_cards:
            card.travel(card.destination.center)
            if get_distance(card.destination.center, card.pos) < card.speed:
                arrived.add(card)
                card.rect.center = card.destination.center
                card.pos = card.rect.center
                if card.destination in self.dealer.hand.slots:
                    self.dealer.hand.cards.append(card)
                    self.dealer.add_slot()
                else:
                    for hand in self.player.hands:
                        if card.destination in hand.slots:
                            hand.cards.append(card)
                            self.player.add_slot(hand)
        self.moving_cards = [x for x in self.moving_cards if x not in arrived]
        self.chip_rack.update()
        self.draw(surface, dt)
        
    def draw(self, surface, dt):
        surface.fill(pg.Color("darkgreen"))
        self.dealer.draw_hand(surface)
        self.deck.draw(surface)
        self.chip_rack.draw(surface)
        self.player.draw(surface)
        for card in self.moving_cards:
            card.draw(surface)  
        for stack in self.moving_stacks:
            stack.draw(surface)
        if self.state == "Betting":
            self.deal_button.draw(surface)
        if self.state == "Player Turn":
            for button in self.player_buttons:
                if button.active:
                    button.draw(surface)
            hand = self.current_player_hand
            rects = [x.rect for x in hand.cards]
            pg.draw.rect(
                        surface, pg.Color("gold3"), 
                        hand.cards[0].rect.unionall(rects).inflate(8, 8), 3)
        if self.state == "Show Results":
            for blinker in self.result_labels:
                blinker.draw(surface, dt)
            self.new_game_button.draw(surface)
        self.lobby_button.draw(surface)
        if self.play_music:
            surface.blit(self.mute_icon, self.music_icon_rect)
        else:
            surface.blit(self.music_icon, self.music_icon_rect)