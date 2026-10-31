// Copyright (C) 2026
//
// Board support for the Arduino Nesso N1 (M5Stack / Arduino)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

#include "Boards.h"

#if BOARD_MODEL == BOARD_NESSO_N1

#include "NessoN1.h"
#include <Wire.h>

#define NESSO_I2C_FREQ 400000

// See NessoN1.h: an explicit bus-0 (FSPI) SPI instance, since the C6 has only
// one general-purpose SPI peripheral (bus index 0).
SPIClass nessoSPI(FSPI);

PI4IOE5V6408 nesso_exp0;
PI4IOE5V6408 nesso_exp1;

PI4IOE5V6408::PI4IOE5V6408() : _addr(0), _present(false) { }

uint8_t PI4IOE5V6408::read_reg(uint8_t reg) {
  Wire.beginTransmission(_addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) { return 0xFF; }
  if (Wire.requestFrom((uint8_t)_addr, (uint8_t)1) != 1) { return 0xFF; }
  if (Wire.available()) { return Wire.read(); }
  return 0xFF;
}

void PI4IOE5V6408::write_reg(uint8_t reg, uint8_t value) {
  Wire.beginTransmission(_addr);
  Wire.write(reg);
  Wire.write(value);
  Wire.endTransmission();
}

void PI4IOE5V6408::write_bit(uint8_t reg, uint8_t bit, bool value) {
  uint8_t reg_value = read_reg(reg);
  if (value) { reg_value |= (1 << bit); }
  else       { reg_value &= ~(1 << bit); }
  write_reg(reg, reg_value);
}

bool PI4IOE5V6408::begin(uint8_t addr) {
  _addr = addr;

  uint8_t id = read_reg(PI4IOE_REG_CTRL);
  // Manufacturer ID 0b101 + firmware rev 0b000 -> upper 6 bits must be 0xA0
  _present = ((id & 0xFC) == 0xA0);
  if (!_present) { return false; }

  // Software reset, as done by the official Arduino_Nesso_N1 library.
  write_reg(PI4IOE_REG_CTRL, 0x01);
  delay(10);

  write_reg(PI4IOE_REG_IN_DEF, 0xFF);    // input default high
  write_reg(PI4IOE_REG_INT_MASK, 0xFF);  // interrupts disabled
  write_reg(PI4IOE_REG_PUD_EN, 0x00);    // no pull-up/pull-down
  write_reg(PI4IOE_REG_PUD_SEL, 0x00);
  write_reg(PI4IOE_REG_DIR, 0x00);       // all inputs for now
  write_reg(PI4IOE_REG_OUT, 0x00);

  return true;
}

void PI4IOE5V6408::pinMode(uint8_t pin, uint8_t mode) {
  if (!_present) { return; }

  if (mode == OUTPUT) {
    write_bit(PI4IOE_REG_PUD_EN, pin, false);
    write_bit(PI4IOE_REG_HIZ, pin, false);
    write_bit(PI4IOE_REG_DIR, pin, true);
  } else {
    write_bit(PI4IOE_REG_DIR, pin, false);
    if (mode == INPUT_PULLUP) {
      write_bit(PI4IOE_REG_PUD_SEL, pin, true);
      write_bit(PI4IOE_REG_PUD_EN, pin, true);
    } else if (mode == INPUT_PULLDOWN) {
      write_bit(PI4IOE_REG_PUD_SEL, pin, false);
      write_bit(PI4IOE_REG_PUD_EN, pin, true);
    } else {
      write_bit(PI4IOE_REG_PUD_EN, pin, false);
    }
  }
}

void PI4IOE5V6408::digitalWrite(uint8_t pin, uint8_t value) {
  write_bit(PI4IOE_REG_OUT, pin, value == HIGH);
}

int PI4IOE5V6408::digitalRead(uint8_t pin) {
  return (read_reg(PI4IOE_REG_IN) & (1 << pin)) ? HIGH : LOW;
}

void nesso_board_init() {
  Wire.begin(I2C_SDA, I2C_SCL, NESSO_I2C_FREQ);

  nesso_exp0.begin(PI4IOE_ADDR_LOW);
  nesso_exp1.begin(PI4IOE_ADDR_HIGH);

  // Expander 0: buttons are active-low and need the internal pull-ups.
  // The LoRa control lines are outputs.
  nesso_exp0.pinMode(NESSO_EXP0_KEY1, INPUT_PULLUP);
  nesso_exp0.pinMode(NESSO_EXP0_KEY2, INPUT_PULLUP);
  nesso_exp0.pinMode(NESSO_EXP0_LNA, OUTPUT);
  nesso_exp0.pinMode(NESSO_EXP0_ANT, OUTPUT);
  nesso_exp0.pinMode(NESSO_EXP0_NRST, OUTPUT);

  // Expander 1: LCD reset/backlight/LED and Grove power as outputs
  nesso_exp1.pinMode(NESSO_EXP1_PWR, OUTPUT);
  nesso_exp1.pinMode(NESSO_EXP1_LCD_RST, OUTPUT);
  nesso_exp1.pinMode(NESSO_EXP1_GROVE, OUTPUT);
  nesso_exp1.pinMode(NESSO_EXP1_LCD_BL, OUTPUT);
  nesso_exp1.pinMode(NESSO_EXP1_LED, OUTPUT);
  nesso_exp1.pinMode(NESSO_EXP1_VIN, INPUT);

  // LCD out of reset, keep backlight off until the display driver is up.
  // POWEROFF is an active-high pulse: keep it LOW during normal operation.
  nesso_exp1.digitalWrite(NESSO_EXP1_LCD_RST, HIGH);
  nesso_exp1.digitalWrite(NESSO_EXP1_LCD_BL, LOW);
  nesso_exp1.digitalWrite(NESSO_EXP1_PWR, LOW);

  // Bring up the LoRa front-end: reset pulse, then antenna switch + LNA
  nesso_lora_reset();
  nesso_rf_enable();
}

void nesso_lora_reset() {
  // SX_NRST low, hold, then high (per Arduino Nesso N1 documentation)
  nesso_exp0.digitalWrite(NESSO_EXP0_NRST, LOW);
  delay(100);
  nesso_exp0.digitalWrite(NESSO_EXP0_NRST, HIGH);
  delay(100);
}

void nesso_rf_rx() {
  // Antenna switch powered, LNA enabled for the receive path.
  // TX/RX direction is handled automatically by the SX1262 DIO2 RF switch.
  nesso_exp0.digitalWrite(NESSO_EXP0_ANT, HIGH);
  nesso_exp0.digitalWrite(NESSO_EXP0_LNA, HIGH);
}

void nesso_rf_enable() {
  nesso_rf_rx();
}

void nesso_rf_tx() {
  // The external LNA must be disabled while transmitting.
  nesso_exp0.digitalWrite(NESSO_EXP0_ANT, HIGH);
  nesso_exp0.digitalWrite(NESSO_EXP0_LNA, LOW);
}

void nesso_rf_disable() {
  nesso_exp0.digitalWrite(NESSO_EXP0_ANT, LOW);
  nesso_exp0.digitalWrite(NESSO_EXP0_LNA, LOW);
}

void nesso_led(bool on) {
  nesso_exp1.digitalWrite(NESSO_EXP1_LED, on ? HIGH : LOW);
}

void nesso_lcd_backlight(bool on) {
  nesso_exp1.digitalWrite(NESSO_EXP1_LCD_BL, on ? HIGH : LOW);
}

void nesso_lcd_reset() {
  // SX_NRST low, hold, then high (per Arduino Nesso N1 documentation)
  nesso_exp1.digitalWrite(NESSO_EXP1_LCD_RST, LOW);
  delay(100);
  nesso_exp1.digitalWrite(NESSO_EXP1_LCD_RST, HIGH);
  delay(100);
}

static bool bq27220_read(uint8_t reg, uint8_t *buf, uint8_t len) {
  Wire.beginTransmission(NESSO_BQ27220_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) { return false; }
  if (Wire.requestFrom((uint8_t)NESSO_BQ27220_ADDR, len) != len) { return false; }
  uint8_t i = 0;
  while (Wire.available() && i < len) { buf[i++] = Wire.read(); }
  return (i == len);
}

bool nesso_battery_present() {
  uint8_t b[2];
  if (!bq27220_read(0x08, b, 2)) { return false; }
  uint16_t mv = (uint16_t)(b[0] | (b[1] << 8));
  return (mv > 0 && mv < 6000);
}

float nesso_battery_voltage() {
  uint8_t b[2];
  if (!bq27220_read(0x08, b, 2)) { return 0.0; }
  return ((float)(b[0] | (b[1] << 8))) / 1000.0;
}

float nesso_battery_soc() {
  uint8_t b[2];
  if (!bq27220_read(0x2C, b, 2)) { return 0.0; }
  return (float)(b[0] | (b[1] << 8));
}

int16_t nesso_battery_current() {
  uint8_t b[2];
  if (!bq27220_read(0x0C, b, 2)) { return 0; }
  return (int16_t)(b[0] | (b[1] << 8));
}

bool nesso_external_power() {
  return (nesso_exp1.digitalRead(NESSO_EXP1_VIN) == HIGH);
}

int nesso_button_read() {
  return nesso_exp0.digitalRead(NESSO_EXP0_KEY1);
}

#endif
