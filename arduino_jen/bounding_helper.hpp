#pragma once

#include <cmath>

#include "global.hpp"

/**
 * bounding_helper 是一個用於計算被界限數值的類別, 透過不斷監察感應器更新的
 * 數據，便可以得知界外數值.
 * 
 * 一些數值例如航向角度被定義在0至359的範圍內, 當機械人向右轉的時候航向角度
 * 會不斷增加, 但是當航向角度超過359的時候, 就會被重新設定為 0
 * 
 * 亦即是說數字0的上一個數字是359, 數值359的下一個數字是 0
 * 
 * 為了方便進行比較, 我們需要一個界外數字, 當航向角度超過359的時候, 該數字不會歸
 * 零, 相反亦可以負數.
 */
class bounding_helper {
  public:
  bool is_close_to_low = false;
  bool is_close_to_high = false;
 
  double tick_limit_low = 0;
  double tick_limit_high = 360;
  double tick_gate = tick_limit_high / 3;
 
  double internal_tick_counter = 0;
  double last_machine_tick = 0;
 
  bounding_helper(const double tick_limit_hight,
                  const double tick_gate)
      : tick_limit_high(tick_limit_hight),
        tick_gate(tick_gate) {}

  bounding_helper(const double tick_limit_hight)
      : tick_limit_high(tick_limit_hight),
        tick_gate(tick_limit_hight / 3) {}

  bounding_helper()
      : tick_limit_high(MOTOR_HIGH_LIMIT),
        tick_gate(MOTOR_HIGH_LIMIT / 3.0) {}
 
  /**
   * 更新最新的界內數字
   * 
   * \param tick
   *        界內數字
   *
   * \return 界外數字
   */
  double operator()(double machine_tick) {
    if (is_close_to_high && machine_tick < tick_limit_low + tick_gate)
      internal_tick_counter += tick_limit_high;
    else if (is_close_to_low && machine_tick > tick_limit_high - tick_gate)
      internal_tick_counter -= tick_limit_high;

    internal_tick_counter += machine_tick - last_machine_tick;

    is_close_to_low = machine_tick < tick_limit_low + tick_gate;
    is_close_to_high = machine_tick > tick_limit_high - tick_gate;
    last_machine_tick = machine_tick;

    return internal_tick_counter;
  }
 
  /**
   * 計算界內數字
   * 
   * \param unbounded
   *        界外數字
   *
   * \return 界內數字
   */
  inline double bound(double unbounded) {
    double ans = std::fmod(unbounded, tick_limit_high);
    if (ans < 0) ans += tick_limit_high;
    return ans;
  }
};