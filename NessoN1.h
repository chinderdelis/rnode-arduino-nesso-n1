// Copyright (C) 2026
//
// Board support for the Arduino Nesso N1 (M5Stack / Arduino)
// ESP32-C6 + SX1262. The LoRa control lines (NRST, ANT_SW, LNA_EN) and the
// front-panel LEDs/LCD reset/backlight are wired to two PI4IOE5V6408 I2C
// GPIO expanders, not to the ESP32-C6 directly.
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

#include "Boards.h"

#ifndef NESSO_N1_H
  #define NESSO_N1_H

  #if BOARD_MODEL == BOARD_NESSO_N1

    #include <Arduino.h>
    #include <SPI.h>

    // The ESP32-C6 exposes a single general-purpose SPI peripheral (bus 0 /
    // FSPI). The SX1262 radio and the ST7789 display share it, so use one
    // explicit bus-0 instance for both instead of the core's global `SPI`.
    extern SPIClass nessoSPI;

    // PI4IOE5V6408 register map
    #define PI4IOE_ADDR_LOW   0x43
    #define PI4IOE_ADDR_HIGH  0x44
    #define PI4IOE_REG_CTRL   0x01
    #define PI4IOE_REG_DIR      0x03
    #define PI4IOE_REG_OUT      0x05
    #define PI4IOE_REG_HIZ      0x07
    #define PI4IOE_REG_IN_DEF   0x09
    #define PI4IOE_REG_PUD_EN   0x0B
    #define PI4IOE_REG_PUD_SEL  0x0D
    #define PI4IOE_REG_IN       0x0F
    #define PI4IOE_REG_INT_MASK 0x11
    #define PI4IOE_REG_INT_STAT 0x13

    // Expander 0 (0x43) pin assignment
    #define NESSO_EXP0_KEY1  0
    #define NESSO_EXP0_KEY2  1
    #define NESSO_EXP0_LNA   5
    #define NESSO_EXP0_ANT   6
    #define NESSO_EXP0_NRST  7

    // Expander 1 (0x44) pin assignment
    #define NESSO_EXP1_PWR   0
    #define NESSO_EXP1_LCD_RST 1
    #define NESSO_EXP1_GROVE 2
    #define NESSO_EXP1_VIN   5
    #define NESSO_EXP1_LCD_BL 6
    #define NESSO_EXP1_LED   7

    class PI4IOE5V6408 {
    public:
      PI4IOE5V6408();

      bool begin(uint8_t addr);
      void pinMode(uint8_t pin, uint8_t mode);
      void digitalWrite(uint8_t pin, uint8_t value);
      int  digitalRead(uint8_t pin);

    private:
      void write_reg(uint8_t reg, uint8_t value);
      uint8_t read_reg(uint8_t reg);
      void write_bit(uint8_t reg, uint8_t bit, bool value);

      uint8_t _addr;
      bool _present;
    };

    extern PI4IOE5V6408 nesso_exp0;
    extern PI4IOE5V6408 nesso_exp1;

    void nesso_board_init();
    void nesso_lora_reset();
    void nesso_rf_enable();
    void nesso_rf_disable();
    void nesso_rf_tx();
    void nesso_rf_rx();
    void nesso_led(bool on);
    void nesso_lcd_backlight(bool on);
    void nesso_lcd_reset();
    int  nesso_button_read();

    // BQ27220 fuel gauge (I2C)
    #define NESSO_BQ27220_ADDR 0x55
    bool nesso_battery_present();
    float nesso_battery_voltage();
    float nesso_battery_soc();
    int16_t nesso_battery_current();
    bool nesso_external_power();

  #endif
#endif
