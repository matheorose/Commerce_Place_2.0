import { CommonModule } from '@angular/common';
import {
  Component,
  Input,
  OnChanges,
  OnDestroy,
  OnInit,
  SimpleChanges,
} from '@angular/core';
import { scaleLinear } from 'd3-scale';
import { fromEvent, Subscription } from 'rxjs';
import { debounceTime } from 'rxjs/operators';

import { USAGES } from '../../data/usages';
import { Usage, UsageType } from '../../models/usage';

@Component({
  selector: 'app-usage-view',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './usage-view.component.html',
  styleUrls: ['./usage-view.component.css'],
})
export class UsageViewComponent implements OnInit, OnChanges, OnDestroy {
  @Input({ required: true }) type: UsageType = 'electricity';

  usages: Usage[] = [];
  average = 0;
  private maxUsage = 0;
  private resizeSub?: Subscription;

  ngOnInit(): void {
    this.updateMetrics(window.innerWidth);

    this.resizeSub = fromEvent(window, 'resize')
      .pipe(debounceTime(150))
      .subscribe(() => this.updateMetrics(window.innerWidth));
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['type']) {
      this.updateMetrics(window.innerWidth);
    }
  }

  ngOnDestroy(): void {
    this.resizeSub?.unsubscribe();
  }

  heightFor(value: number) {
    if (!this.maxUsage) {
      return 0;
    }

    return scaleLinear()
      .domain([0, this.maxUsage])
      .range([0, 150])(value);
  }

  trackUsageByDay(_index: number, usage: Usage) {
    return usage.day;
  }

  get unitLabel() {
    if (this.type === 'electricity') {
      return 'kWh';
    }
    if (this.type === 'gas') {
      return 'm³';
    }
    return 'L';
  }

  totalBarClass() {
    if (this.type === 'electricity') {
      return 'bg-green-100';
    }

    if (this.type === 'gas') {
      return 'bg-orange-500';
    }

    return 'bg-blue-500';
  }

  cleanBarClass() {
    return 'bg-green-500';
  }

  totalLegendBackground() {
    if (this.type === 'electricity') {
      return 'bg-green-100';
    }

    if (this.type === 'gas') {
      return 'bg-orange-500';
    }

    return 'bg-blue-500';
  }

  private updateMetrics(width: number) {
    const limit = width < 768 ? 7 : 14;
    const next = USAGES[this.type].slice(0, limit);
    this.usages = next;
    this.maxUsage = Math.max(...next.map((usage) => usage.amount));
    this.average =
      next.reduce((acc, usage) => acc + usage.amount, 0) / Math.max(next.length, 1);
  }
}
