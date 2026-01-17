import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { scaleLinear } from 'd3-scale';

import { Hub } from '../../models/hub';
import { GaugeIconComponent } from '../icons/gauge-icon/gauge-icon.component';
import { LightningIconComponent } from '../icons/lightning-icon/lightning-icon.component';
import { LockIconComponent } from '../icons/lock-icon/lock-icon.component';

@Component({
  selector: 'app-hub-view',
  standalone: true,
  imports: [CommonModule, GaugeIconComponent, LightningIconComponent, LockIconComponent],
  templateUrl: './hub-view.component.html',
  styleUrls: ['./hub-view.component.css'],
})
export class HubViewComponent {
  @Input({ required: true }) hub!: Hub;

  get lightsOn() {
    return this.hub?.lights.filter((light) => light.status).length ?? 0;
  }

  get locksLocked() {
    return this.hub?.locks.filter((lock) => lock.isLocked).length ?? 0;
  }

  get lightsHeight() {
    if (!this.hub) {
      return 0;
    }

    const countToHeight = scaleLinear<number>()
      .domain([0, this.hub.lights.length])
      .range([0, 32]);

    return countToHeight(this.lightsOn);
  }
}
